
import sqlite3

c = sqlite3.connect('healer_nexus.db')

c.execute("""UPDATE specialists SET

    name='ариса озубаль',

    specialty='читель математики та української мови',

    bio='освідчений педагог з 30+ років стажу. ндивідуальний підхід до кожного учня. уже гарна людина.'

    WHERE id=5""")

c.execute("""UPDATE practitioner_profiles SET

    unique_story=' вірю що кожна дитина здатна зрозуміти математику якщо пояснити правильно. ій досвід допомагає знайти підхід до кожного.',

    contact_link='https://t.me/larisa_kozubal',

    creator_signature='ариса озубаль'

    WHERE id=3""")

c.execute("DELETE FROM users WHERE id=2")

c.execute("DELETE FROM practitioner_profiles WHERE specialist_id=4")

c.execute("DELETE FROM specialists WHERE id=4")

c.commit()

print("OK! Larisa updated, test account removed")

c.close()

