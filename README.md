# hslu_rrc_demo

Mini-Demo für die HSLU RRC-Anlage (ABB GoFa + Güdel-Track + Zimmer-Gripper +
Kreissäge). Macht nichts Sinnvolles — fährt nur ein paar fix programmierte
Bewegungen, klickt mit dem Gripper und lässt zwischendurch die Säge
aufheulen.

Gedacht für Vorführungen, wenn die Anlage einfach ein bisschen Lärm und
Bewegung machen soll.

## Voraussetzungen

- Docker mit `compasrrc/compas_rrc_driver:v1.1.2`
- Python 3.x mit `compas_rrc` und `compas_fab` installiert
- Anlage entweder real erreichbar (`192.168.50.240`) oder als virtueller
  Controller in RobotStudio gestartet (`host.docker.internal`)
- RAPID-Module mit den Custom-Instruktionen `r_Gudel_HSLU_MoveToJoints`,
  `r_HSLU_GripperOpen/Close`, `r_HSLU_SawOn/Off` auf der Steuerung

## Setup

```bash
pip install compas_rrc compas_fab
```

`docker/docker-compose.yml` enthält bereits Profile für virtuelle und reale
Steuerung — die nicht benötigte Zeile auskommentieren.

## Verwendung

```bash
# 1. Docker starten (ROS-Master, Bridge, ABB-Driver)
cd docker
docker-compose up

# 2. In zweitem Terminal Demo starten
python demo.py
```

Vorher in `demo.py` anpassen:

| Flag          | Wirkung                                                   |
|---------------|-----------------------------------------------------------|
| `DRY_RUN`     | True = keine Verbindung, nur prints                       |
| `N_LOOPS`     | Wie oft die Choreografie wiederholt wird                  |
| `USE_SAW`     | Säge an/aus zwischendurch — laut!                         |
| `USE_GRIPPER` | Gripper-Klicken zwischendurch                             |

## Was passiert in einem Loop

1. Home-Position anfahren
2. Gripper 3x klicken
3. Track-Sweep links→rechts (lange Fahrt)
4. Säge 1.5s aufheulen
5. Wiggle (hoch/tief schnell hintereinander)
6. Gripper zu, Säge 2.5s, Gripper auf
7. Twist (J4/J6 in beide Richtungen verdrehen)
8. Zurück zu Home

Strg+C bricht ab; Säge wird im `finally`-Block ausgeschaltet, der Roboter
bleibt aber wo er gerade ist.

## Sicherheit

- Vor dem ersten Lauf gegen virtuellen Controller testen (DRY_RUN=False,
  RobotStudio mit virtueller Steuerung).
- Track-Werte sind im erlaubten Bereich 0…2900 mm.
- Joint-Werte konservativ gewählt, keine Annäherung an Singularitäten.
- Speed ist über `time_s` pro Move begrenzt (3–5 s pro Bewegung).
- Die Choreografie fährt NICHT durch das Sägeblatt — Säge läuft nur
  zum Lärm machen, der Roboter bleibt währenddessen in sicherer Distanz.

## Herkunft

Bausteine (custom_motion, Gripper-Calls, RAPID-Instruktionen, Joint-Limits)
stammen aus dem Swissbau-2026-Projekt
(`hslu_rrc_Swissbau26/src/rrc_swissbau`).
