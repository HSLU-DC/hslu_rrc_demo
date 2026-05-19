"""HSLU RRC Demo — Lärm & Bewegung für die Anlage.

Kleines Demo-Programm: fix programmierte Track-+Roboter-Bewegungen, Gripper
auf/zu und Kreissäge an/aus. Kein Fab-Data, keine Stationen, keine Logik —
einfach Choreografie für Vorführungen.

Verwendung:
    1. Docker starten:        cd docker && docker-compose up
    2. CONTROLLER unten setzen (VIRTUAL / REAL).
    3. Optional DRY_RUN=True, um ohne Robot-Verbindung zu testen (alle
       Bewegungen werden nur ausgegeben, nichts wird gesendet).
    4. python demo.py
    5. Strg+C bricht ab; der Robot fährt dann nicht mehr automatisch
       in Home, also vor dem Stop überlegen.
"""

from __future__ import annotations

import time
import compas_rrc as rrc
from compas_rrc.common import ExecutionLevel, FeedbackLevel
from compas_fab.backends.ros.messages import ROSmsg


# ==============================================================================
# RUN CONFIG
# ==============================================================================
ROBOT_NAME = "/rob1"
TOOL_GRIPPER = "t_HSLU_GripperZimmer"

DRY_RUN = False        # True: keine Robot-Verbindung, nur prints
N_LOOPS = 3            # Wie oft die Choreografie wiederholt wird
USE_SAW = True         # Kreissäge an/aus zwischendurch (laut!)
USE_GRIPPER = True     # Gripper auf/zu zwischendurch (klick-klick)


# ==============================================================================
# Custom Motion — kopiert aus rrc_swissbau.skills.custom_motion
# ==============================================================================
# Coordinated track + robot move via Güdel-spezifische RAPID-Instruktion.
# 'time' ist in SEKUNDEN (nicht Speed), weil Track und Roboter gleichzeitig
# ankommen müssen.

INSTRUCTION_PREFIX = "r_Gudel_HSLU_"


class MoveToJoints(ROSmsg):
    """Coordinated joint move (robot axes + Güdel track)."""

    def __init__(self, joints, ext_axes, speed, zone, feedback_level=FeedbackLevel.NONE):
        if speed <= 0:
            raise ValueError("Speed must be > 0")

        self.instruction = INSTRUCTION_PREFIX + "MoveToJoints"
        self.feedback_level = feedback_level
        self.exec_level = ExecutionLevel.ROBOT

        joints = joints or []
        joints_pad = [0.0] * (6 - len(joints))
        ext_axes = ext_axes or []
        ext_axes_pad = [0.0] * (6 - len(ext_axes))

        self.string_values = []
        self.float_values = (
            list(joints) + joints_pad + list(ext_axes) + ext_axes_pad + [speed, zone]
        )


# ==============================================================================
# Choreografie-Positionen
# ==============================================================================
# Format: ([J1..J6 in deg], [Track in mm 0..2900])
# Werte stammen teilweise aus dem Swissbau-Repo (jp_home, jp_park etc.)
# und ein paar selbst zusammengestellte Wackel-Posen.

POS_HOME =    ([ -40,  20,   0,   0,  70, -40], [ 500.0])   # jp_home aus hslu_rrc_facade — safe pose for start/end

# "Ganz rüber" — gleiche Roboter-Pose, Track ans andere Ende (mit Reserve zum Limit 2900)
POS_FAR =     ([ -40,  20,   0,   0,  70, -40], [2800.0])

# "Hoch / runter" am Home-Ort — Track bleibt bei 500, nur J2/J3 variieren
POS_UP =      ([ -40,   0, -15,   0,  60, -40], [ 500.0])
POS_DOWN =    ([ -40,  35,  15,   0,  80, -40], [ 500.0])

# "Twist" am Home-Ort — Track bleibt bei 500, J4 & J6 verdrehen
POS_TWIST_A = ([ -40,  20,   0,  60,  70,  20], [ 500.0])
POS_TWIST_B = ([ -40,  20,   0, -60,  70, -100], [ 500.0])


# ==============================================================================
# Hilfs-Calls
# ==============================================================================
def move(r1, pos, *, time_s=3.0, zone=None):
    """Coordinated move zu einer Choreografie-Pose."""
    joints, ext = pos
    if zone is None:
        zone = rrc.Zone.Z50
    if DRY_RUN or r1 is None:
        print(f"  [MOVE] joints={joints} track={ext} time={time_s}s")
        return
    r1.send_and_wait(MoveToJoints(joints, ext, time_s, zone))


def gripper_open(r1):
    if not USE_GRIPPER:
        return
    if DRY_RUN or r1 is None:
        print("  [GRIPPER] open")
        return
    r1.send_and_wait(rrc.CustomInstruction("r_HSLU_GripperOpen", [], []))


def gripper_close(r1):
    if not USE_GRIPPER:
        return
    if DRY_RUN or r1 is None:
        print("  [GRIPPER] close")
        return
    r1.send_and_wait(rrc.CustomInstruction("r_HSLU_GripperClose", [], []))


def saw_on(r1):
    if not USE_SAW:
        return
    if DRY_RUN or r1 is None:
        print("  [SAW] ON")
        return
    r1.send_and_wait(rrc.CustomInstruction("r_HSLU_SawOn", [], []))


def saw_off(r1):
    if not USE_SAW:
        return
    if DRY_RUN or r1 is None:
        print("  [SAW] OFF")
        return
    r1.send_and_wait(rrc.CustomInstruction("r_HSLU_SawOff", [], []))


def wait(r1, seconds):
    """Wartet — entweder per WaitTime auf der Steuerung oder lokal."""
    if DRY_RUN or r1 is None:
        print(f"  [WAIT] {seconds}s")
        time.sleep(seconds)
        return
    r1.send_and_wait(rrc.WaitTime(seconds))


# ==============================================================================
# Choreografien
# ==============================================================================
def gripper_play(r1, n=4):
    """Klick-klick-klick — Gripper mehrmals auf/zu."""
    print("[ACT] Gripper-Spiel")
    for _ in range(n):
        gripper_close(r1)
        wait(r1, 0.3)
        gripper_open(r1)
        wait(r1, 0.3)


def saw_burst(r1, duration=2.0):
    """Säge kurz aufheulen lassen."""
    print(f"[ACT] Säge {duration}s an")
    saw_on(r1)
    wait(r1, duration)
    saw_off(r1)


def track_far_and_back(r1, *, saw_at_far=False):
    """Von Home aus ganz rüber an den Track-Anschlag und wieder zurück.

    Wenn ``saw_at_far`` gesetzt ist, wird die Säge am Anschlag kurz
    aufgeheult — dort ist der Roboter weit weg von allem und sicher.
    """
    print("[ACT] Track rüber & zurück")
    move(r1, POS_FAR, time_s=6.0)
    if saw_at_far:
        saw_burst(r1, duration=2.0)
    move(r1, POS_HOME, time_s=6.0)


def up_down(r1):
    """Am Home-Ort hoch und runter (J2/J3)."""
    print("[ACT] Hoch/Runter")
    move(r1, POS_UP, time_s=2.0)
    move(r1, POS_DOWN, time_s=2.0)
    move(r1, POS_UP, time_s=2.0)
    move(r1, POS_DOWN, time_s=2.0)


def twist(r1):
    """Am Home-Ort verdrehen (J4/J6)."""
    print("[ACT] Twist")
    move(r1, POS_TWIST_A, time_s=3.0)
    move(r1, POS_TWIST_B, time_s=3.0)


# ==============================================================================
# Main
# ==============================================================================
def run_choreography(r1, loop_idx):
    """Eine Runde Demo:
       Home → ganz rüber → zurück → hoch/runter → twist → Home.
       Gripper-Klick und Säge-Burst sind drumrum platziert.
    """
    print(f"\n===== LOOP {loop_idx + 1}/{N_LOOPS} =====")

    # Start in Home, kurzes Gripper-Klicken zur Ankündigung
    move(r1, POS_HOME, time_s=4.0)
    gripper_play(r1, n=2)

    # Track ganz rüber, dort Säge aufheulen (weit weg von allem), dann zurück
    track_far_and_back(r1, saw_at_far=True)

    # Am Home-Ort hoch/runter und twist
    up_down(r1)
    twist(r1)

    # Zurück in Home
    move(r1, POS_HOME, time_s=4.0)
    gripper_open(r1)


def main():
    if DRY_RUN:
        print("=== DRY RUN — keine Robot-Verbindung ===")
        r1 = None
        ros = None
    else:
        ros = rrc.RosClient()
        ros.run()
        r1 = rrc.AbbClient(ros, ROBOT_NAME)
        print(f"Connected to {ROBOT_NAME}")
        r1.send(rrc.SetTool(TOOL_GRIPPER))

    try:
        for i in range(N_LOOPS):
            run_choreography(r1, i)

        print("\n===== Demo fertig — fahre Home =====")
        move(r1, POS_HOME, time_s=4.0)
        gripper_open(r1)

    except KeyboardInterrupt:
        print("\n[!] Abbruch durch Benutzer — Roboter bleibt stehen.")
        saw_off(r1)
    finally:
        if not DRY_RUN and ros is not None:
            ros.close()
            ros.terminate()
            print("Disconnected.")


if __name__ == "__main__":
    main()
