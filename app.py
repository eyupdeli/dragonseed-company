from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import dao

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dragonseed-company-2026'

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# the app's fixed vocabulary, every valid day, location, quest type and so on
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
LOCATIONS = ['Driftmark Shores', 'The Gullet Straits', 'Dragonmont Eyrie']
TYPES = ['combat', 'exploration', 'puzzle', 'stealth', 'magic', 'survival']
DIFFICULTIES = ['easy', 'medium', 'hard', 'legendary']
CAPACITY = {'Warrior': 4, 'Mage': 3, 'Healer': 2}
IMAGES = ['riddle.jpg', 'duel.jpg', 'flight.jpg', 'smuggler.jpg', 'storm.jpg', 'scrolls.jpg']

# simulated current day and time of the fictional week
SIM_DAY = 2        # 0 = Monday, so 2 = Wednesday
SIM_TIME = '17:00'


# position inside the fictional week, in minutes from Monday 00:00
def to_minutes(day, time):
    hours, minutes = time.split(':')
    return day * 24 * 60 + int(hours) * 60 + int(minutes)


NOW = to_minutes(SIM_DAY, SIM_TIME)


# pass these to every template so we don't repeat them in each route
@app.context_processor
def template_globals():
    return dict(DAYS=DAYS, LOCATIONS=LOCATIONS, TYPES=TYPES, DIFFICULTIES=DIFFICULTIES,
                CAPACITY=CAPACITY, IMAGES=IMAGES, NOW=NOW, SIM_DAY=SIM_DAY, SIM_TIME=SIM_TIME)

# Flask login needs an object with these attributes, not a raw database row
class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.username = row['username']
        self.role = row['role']


@login_manager.user_loader
def load_user(user_id):
    row = dao.get_user_by_id(user_id)
    return User(row) if row else None


# turn each raw session row into everything the templates need: timing + free/taken places
def prepare_sessions(sessions):
    counts = dao.get_role_counts()
    for s in sessions:
        s['start'] = to_minutes(s['day'], s['start_time'])
        s['end'] = s['start'] + s['duration']
        s['taken'] = {role: counts.get((s['id'], role), 0) for role in CAPACITY}
        s['free'] = {role: CAPACITY[role] - s['taken'][role] for role in CAPACITY}
        s['booked'] = sum(s['taken'].values())
    return sessions


def valid_time(value):
    parts = value.split(':')
    return (len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()
            and int(parts[0]) < 24 and int(parts[1]) < 60)


# ---------- public pages ----------

@app.route('/')
def index():
    sessions = prepare_sessions(dao.get_sessions())
    day = request.args.get('day', '')
    if day.isdigit():
        sessions = [s for s in sessions if s['day'] == int(day)]
    qtype = request.args.get('type', '')
    if qtype:
        sessions = [s for s in sessions if s['type'] == qtype]
    difficulty = request.args.get('difficulty', '')
    if difficulty:
        sessions = [s for s in sessions if s['difficulty'] == difficulty]
    role = request.args.get('role', '')
    if role in CAPACITY:
        sessions = [s for s in sessions if s['free'][role] > 0]
    return render_template('index.html', sessions=sessions, filters=request.args)


@app.route('/session/<int:session_id>')
def session_detail(session_id):
    s = dao.get_session(session_id)
    if s is None:
        abort(404)
    s = prepare_sessions([s])[0]
    others = [o for o in dao.get_sessions() if o['quest_id'] == s['quest_id'] and o['id'] != s['id']]
    mine = None
    participants = None
    if current_user.is_authenticated:
        if current_user.role == 'adventurer':
            mine = dao.get_participation(current_user.id, session_id)
        else:
            participants = dao.get_session_participations(session_id)
    return render_template('session.html', s=s, others=others, mine=mine, participants=participants)


# ---------- adventurer actions ----------

@app.route('/session/<int:session_id>/join', methods=['POST'])
@login_required
def join(session_id):
    if current_user.role != 'adventurer':
        abort(403)
    s = dao.get_session(session_id)
    if s is None:
        abort(404)
    s = prepare_sessions([s])[0]
    role = request.form.get('role', '')
    places = request.form.get('places', '')
    mine = dao.get_user_participations(current_user.id)

    error = None
    if role not in CAPACITY or places not in ('1', '2'):
        error = 'Please choose a valid role and number of places.'
    elif s['start'] <= NOW:
        error = 'This session has already started, joining is closed.'
    elif dao.get_participation(current_user.id, session_id):
        error = 'You already joined this session.'
    elif len(mine) >= 3:
        error = 'You can join at most 3 quest sessions per week.'
    elif int(places) > s['free'][role]:
        error = f'Not enough {role} places left ({s["free"][role]} free).'
    else:
        # reject if this session's time window overlaps any session the adventurer already joined
        for p in mine:
            p_start = to_minutes(p['day'], p['start_time'])
            if p_start < s['end'] and s['start'] < p_start + p['duration']:
                error = f'This session overlaps with "{p["title"]}", which you already joined.'
    if error:
        flash(error, 'danger')
    else:
        dao.add_participation(session_id, current_user.id, role, int(places))
        flash(f'You joined as {role} with {places} place(s). Fire and blood!', 'success')
    return redirect(url_for('session_detail', session_id=session_id))


@app.route('/participation/<int:part_id>/cancel', methods=['POST'])
@login_required
def cancel(part_id):
    p = dao.get_participation_by_id(part_id)
    if p is None or p['user_id'] != current_user.id:
        abort(403)
    # participations are frozen from 8 hours before the session starts
    if to_minutes(p['day'], p['start_time']) - NOW <= 8 * 60:
        flash('This session starts within 8 hours: the participation can no longer be changed.', 'danger')
    else:
        dao.delete_participation(part_id)
        flash('Participation cancelled.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile')
@login_required
def profile():
    if current_user.role == 'master':
        return redirect(url_for('manage'))
    if current_user.role == 'council':
        return redirect(url_for('council'))
    participations = dao.get_user_participations(current_user.id)
    for p in participations:
        p['locked'] = to_minutes(p['day'], p['start_time']) - NOW <= 8 * 60
    return render_template('profile.html', participations=participations)


# ---------- guild master ----------

@app.route('/manage')
@login_required
def manage():
    if current_user.role != 'master':
        abort(403)
    sessions = prepare_sessions(dao.get_sessions())
    # quests without any sessions yet won't appear above, so list them here too
    scheduled = {s['quest_id'] for s in sessions}
    unscheduled = [q for q in dao.get_quests() if q['id'] not in scheduled]
    return render_template('manage.html', sessions=sessions, unscheduled=unscheduled)


@app.route('/quest/new', methods=['GET', 'POST'])
@login_required
def new_quest():
    if current_user.role != 'master':
        abort(403)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        duration = request.form.get('duration', '')
        qtype = request.form.get('type', '')
        difficulty = request.form.get('difficulty', '')
        image = request.form.get('image', '')
        if (not title or not description or qtype not in TYPES or difficulty not in DIFFICULTIES
                or image not in IMAGES or not duration.isdigit() or not 15 <= int(duration) <= 480):
            flash('Please fill in every field with valid values.', 'danger')
        else:
            dao.add_quest(title, qtype, difficulty, int(duration), description, image)
            flash('Quest created. Remember: quests cannot be modified afterwards.', 'success')
            return redirect(url_for('manage'))
    return render_template('quest_form.html')


# one function handles both "create" and "edit" since the form and the overlap
# check are the same either way, session_id is None when creating a new session
@app.route('/session/new', methods=['GET', 'POST'])
@app.route('/session/<int:session_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_session(session_id=None):
    if current_user.role != 'master':
        abort(403)
    editing = None
    if session_id is not None:
        editing = dao.get_session(session_id)
        if editing is None:
            abort(404)
        # once someone has joined, the day/time/location are locked for good
        if dao.count_participants(session_id) > 0:
            flash('Adventurers already joined this session, it cannot be changed anymore.', 'danger')
            return redirect(url_for('manage'))
    if request.method == 'POST':
        day = request.form.get('day', '')
        start_time = request.form.get('start_time', '')
        location = request.form.get('location', '')
        quest_id = str(editing['quest_id']) if editing else request.form.get('quest_id', '')
        quest = dao.get_quest(int(quest_id)) if quest_id.isdigit() else None
        if (quest is None or not day.isdigit() or int(day) > 6
                or location not in LOCATIONS or not valid_time(start_time)):
            flash('Please fill in every field with valid values.', 'danger')
        else:
            # two sessions at the same location clash if their time windows overlap
            start = to_minutes(int(day), start_time)
            end = start + quest['duration']
            clash = None
            for other in prepare_sessions(dao.get_sessions()):
                if (other['location'] == location and other['id'] != session_id
                        and other['start'] < end and start < other['end']):
                    clash = other
            if clash:
                flash(f'{location} is taken by "{clash["title"]}" on {DAYS[clash["day"]]} '
                      f'at {clash["start_time"]}.', 'danger')
            else:
                if editing:
                    dao.update_session(session_id, int(day), start_time, location)
                    flash('Session updated.', 'success')
                else:
                    dao.add_session(int(quest_id), int(day), start_time, location)
                    flash('Session scheduled.', 'success')
                return redirect(url_for('manage'))
    return render_template('session_form.html', editing=editing, quests=dao.get_quests())


@app.route('/session/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    if current_user.role != 'master':
        abort(403)
    # same rule as editing, can't cancel a session once someone joined it
    if dao.count_participants(session_id) > 0:
        flash('Adventurers already joined this session, it cannot be cancelled.', 'danger')
    else:
        dao.delete_session(session_id)
        flash('Session cancelled.', 'success')
    return redirect(url_for('manage'))


# ---------- guild council administrator (prova finale) ----------

# read-only page, pulls together everything the council needs to see in one place
@app.route('/council')
@login_required
def council():
    if current_user.role != 'council':
        abort(403)
    return render_template('council.html', stats=dao.get_platform_stats(),
                           adventurers=dao.get_adventurers(),
                           sessions=prepare_sessions(dao.get_sessions()))


# ---------- authentication ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if len(username) < 3 or len(password) < 6:
            flash('Username needs at least 3 characters and password at least 6.', 'danger')
        elif dao.get_user_by_username(username):
            flash('That username is already taken.', 'danger')
        else:
            dao.add_user(username, generate_password_hash(password))
            flash('Welcome to the Dragonseed Company! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        row = dao.get_user_by_username(request.form.get('username', '').strip())
        if row and check_password_hash(row['password'], request.form.get('password', '')):
            login_user(User(row))
            return redirect(url_for('index'))
        flash('Wrong username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ---------- error pages ----------

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, title='No dragons for you here',
                            message='You have wandered into a part of the Company that is not yours '
                                    'to enter. Turn back now, before the dragon notices.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, title='This dragon could not be found',
                            message="Whatever you were looking for has flown off. Even the maesters "
                                    "have no record of it."), 404


if __name__ == '__main__':
    app.run(debug=True)
