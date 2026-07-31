# The Dragonseed Company — Guild Management Web App

A fantasy adventure guild set during the Dance of the Dragons: low-born dragonseeds
racing to claim masterless dragons around Driftmark and the Gullet.

## Deployed application

https://eyupdeli.pythonanywhere.com

## Simulated current day and time

**Wednesday 17:00** — defined by the `SIM_DAY` / `SIM_TIME` constants at the top
of `app.py` and shown in the navbar of every page.

Because of this, sessions on Monday, Tuesday and Wednesday morning are already in
the past, and every participation in a session starting before **Thursday 01:00**
is locked by the 8-hour rule.

## Test accounts

All sample accounts use the same password: **northRemembers**

| username    | role                                          |
|-------------|-----------------------------------------------|
| guildmaster | Guild Master (creates quests and sessions)    |
| council     | Guild Council administrator                   |
| rhaenyra    | adventurer                                    |
| daemon      | adventurer                                    |
| aemond      | adventurer                                    |
| jacaerys    | adventurer                                    |

## Sample data worth testing

- **Fully booked role**: "Duel Above the Gullet", Thursday 20:00 — both Healer
  places are taken, so joining as Healer is refused.
- **Locked participations**: daemon joined "Storm Over the Gullet" (Wednesday
  21:00, starts in 4 hours) and a Monday session that is already over — neither
  can be cancelled.
- **Modifiable participations**: aemond and jacaerys have Saturday
  participations that can still be cancelled.
- **Editable session**: "Riddle of the Riderless Dragon" on Thursday 14:00 has
  no participants, so the Guild Master can edit or cancel it.

## Running locally

```
pip install -r requirements.txt
python init_db.py      # recreates guild.db with the sample data above
python app.py          # http://127.0.0.1:5000
```

## Notes

- Target device: **desktop** (tested on current Chrome and Firefox).
- Passwords are stored hashed (werkzeug). All SQL uses parameterized queries.
