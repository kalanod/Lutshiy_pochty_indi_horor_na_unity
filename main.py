import glob
import locale

from flask import Flask, redirect, render_template
from flask_login import LoginManager, logout_user, login_required

from flask_restful import reqparse, abort, Api, Resource
from flask import Flask, render_template, redirect, request
from forms.register import RegisterForm
from forms.login import LoginForm
from flask import make_response
from flask import jsonify
from requests import get, post
from flask_login import login_user, logout_user, current_user

from data import db_session
from data.users import User
from data import users_resource
from data.rooms import Rooms
from data import rooms_resource
from data.news import News
from data import news_resource
from in_game import *
from flask_socketio import SocketIO, send, emit, join_room, leave_room
import os
import random
import time
from flask import make_response

# print(os.getcwd())

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'key'

default_language = 'en_US'
locale.setlocale(locale.LC_ALL, default_language + ".utf8")
languages = {}
language_list = glob.glob("language/*.json")
for lang in language_list:
    filename = lang.split('/')
    lang_code = filename[1].split('.')[0]
    with open(lang, 'r', encoding='utf8') as file:
        languages[lang_code] = json.loads(file.read())
login_manager = LoginManager()
login_manager.init_app(app)
socketIO = SocketIO(app)
api.add_resource(users_resource.UserListResource, '/api/users')
api.add_resource(users_resource.UserResource, '/api/users/<int:users_id>')
api.add_resource(rooms_resource.RoomsListResource, '/api/rooms')
api.add_resource(rooms_resource.RoomsResource, '/api/rooms/<int:rooms_id>')
api.add_resource(news_resource.NewsListResource, '/api/news')
api.add_resource(news_resource.NewsResource, '/api/news/<int:news_id>')
active_rooms = []  # список со всеми комнатами


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found - 404'}), 404)


@app.errorhandler(405)
def method_not_allowed(error):
    return make_response(jsonify({'error': 'Method Not Allowed - 405'}), 405)


@app.route('/rooms', methods=['GET', 'POST'])
def base():
    lang = request.args.get('lang')
    if lang is None or lang not in languages:
        lang = default_language
    params = dict()
    params["title"] = "Список комнат"
    params["rooms"] = active_rooms
    return render_template('index.html', **params, **languages[lang])


@app.route('/', methods=['GET', 'POST'])
def news():
    lang = request.args.get('lang')
    if lang is None or lang not in languages:
        lang = default_language
    db_sess = db_session.create_session()
    params = dict()
    params["title"] = "Новости"
    params["news_list"] = reversed(db_sess.query(News).all())
    print(params["news_list"])

    return render_template('news.html', **params, **languages[lang])


@app.route('/devs', methods=['GET', 'POST'])
def devs():
    lang_param = request.args.get('lang')

    if lang_param is not None and lang_param in languages:
        lang = lang_param

    else:
        lang = request.cookies.get("language")
        if lang is None or lang not in languages:
            lang = default_language


    params = dict()
    params["title"] = languages[lang]["title_dev"]
    if (lang == "ru_RU"):
        params["devs_list"] = [{"nickname": "Михаил Буянов",
                                 "dev": ["дизайн)))",
                                         "бэкенд"],
                                 "link_text": "VK",
                                 "link": "https://vk.com/deep_dark_fantasies_vana"},
                                {"nickname": "Прошак Валерий",
                                 "dev": ["написал 10 строчек кода"],
                                 "link_text": "VK",
                                 "link": "https://vk.com/vproshak"},
                                {"nickname": "Андрей Трофимов",
                                 "dev": ["фронтенд", "обмен данными с сервером"],
                                 "link_text": "VK",
                                 "link": "https://vk.com/kalanod"},
                                {"nickname": "Влад Ревякин",
                                 "dev": ["написал события", "отдыхал"],
                                 "link_text": "VK",
                                 "link": "https://vk.com/id515647622"}
                                ]
    else:
        params["devs_list"] = [{"nickname": "Mikhail Buyanov",
                                "dev": ["design)))",
                                        "backend"],
                                "link_text": "VK",
                                "link": "https://vk.com/deep_dark_fantasies_vana"},
                               {"nickname": "Proshak Valeri",
                                "dev": ["did nothing"],
                                "link_text": "VK",
                                "link": "https://vk.com/vproshak"},
                               {"nickname": "Andrew Trofimov",
                                "dev": ["frontend"],
                                "link_text": "VK",
                                "link": "https://vk.com/kalanod"},
                               {"nickname": "Vlad Reviakin",
                                "dev": ["in-game events"],
                                "link_text": "VK",
                                "link": "https://vk.com/id515647622"}
                               ]
    res = make_response(render_template('devs.html', **params, **languages[lang]))
    if lang_param is not None and lang_param in languages:
        res.set_cookie("language", lang_param)
    return res


@app.route('/login', methods=['GET', 'POST'])
def login():
    lang = request.args.get('lang')
    if lang is None or lang not in languages:
        lang = default_language

    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            param = dict()
            param["title"] = "Успех"
            return redirect('/')
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form, **languages[lang])
    return render_template('login.html', title='Авторизация', form=form, **languages[lang])


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    lang = request.args.get('lang')
    if lang is None or lang not in languages:
        lang = default_language
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают", **languages[lang])
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть", **languages[lang])
        user = User(
            nickname=form.nickname.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form, **languages[lang])


@app.route('/create_room/<title>/<creator_id>')
def create_room(title, creator_id):
    print('creating room', title, creator_id)
    db_sess = db_session.create_session()
    id = random.randint(1, 2 ** 32)
    room = Rooms(
        id=id,
        title=title,
        creator=creator_id,
        data='',
        players=''
    )
    db_sess.add(room)

    db_sess.commit()

    active_rooms.append(InGameRoom(id, title))
    # return redirect('/')
    # нам надо на главную страницу, а не результат
    return redirect('/rooms')


@app.route('/connect_to_room/<int:room_id>/<int:player_id>', methods=['GET', 'POST'])
def connect_to_room(room_id, player_id):
    room = get_room(room_id)
    if room.player_in_room(player_id) or room.stage == -1:
        room.add_player(player_id)
        return redirect(f'/room/{room_id}')

    else:
        return redirect('/rooms')

@app.route('/test', methods=['GET', 'POST'])
def path_test():
    if request.method == 'POST':
        value = request.values.get('value')
        return f"<p>method is POST and value is {value}</p>"
    else:
        return "<p>method is GET</p>"


@app.route('/leave_from_room/<int:room_id>/<int:player_id>', methods=['GET', 'POST'])
def leave_from_room(room_id, player_id):
    # какие-нибудь проверки
    get_room(room_id).leave_player(player_id)
    return redirect('/rooms')


@app.route('/room/<int:room_id>', methods=['GET', 'POST'])
def in_room(room_id):
    lang = request.args.get('lang')
    if lang is None or lang not in languages:
        lang = default_language
    current_room = get_room(room_id)
    return render_template('in_room.html', current_room=current_room, title="В игре", **languages[lang])


@socketIO.on('decision')
def make_decision(json):
    print('get_decision from server')
    print(f'json: {json}')
    data = ''
    if json['code'] == '1':
        data = 'Игрок готов'
        log(json['room_id'], data)
    elif json['code'] == '2':
        data = f'Выбор карты акций {list(json.keys())[-1]} от 0 до 2 покупка будет происходить во время аукциона'
        log(json['room_id'], data)
    elif json['code'] == '3':
        data = 'Продажа акций'
        log(json['room_id'], data)
    elif json['code'] == '4':
        data = 'Покупка недвижимости'
        log(json['room_id'], data)
        for _, i in enumerate(get_room(json['room_id']).realty_list):
            if i.name == json['title']:
                idd = _ + 1
                json['company_id'] = idd
    elif json['code'] == '5':
        data = 'Покупка недвижимости'
        log(json['room_id'], data)

    room_id = int(json['room_id'])
    room = get_room(room_id)
    room.add_decision_to_queue(json)
    # пока добавим обработку всех решений в очереди сюда
    room.decision_handler()
    players = [len(room.players), len([i for i in room.players if i.ready])]
    emit('make_turn', players, to=room_id)
    emit('decision_on', to=room_id)

    stonks = {'id': int(json['player_id']), 'data': [
        {'short_name': i.short_name, 'cost': i.cost, 'stocks': room.get_player(int(json['player_id'])).stocks[i]} for i
        in room.get_player(int(json['player_id'])).stocks]}

    emit('update_bag', stonks, to=room_id)

    # Это просто обновление недвижимости
    com = {}
    for i in room.realty_list:
        if i.owner:
            com[i.name] = i.owner.id
        else:
            com[i.name] = None
    com1 = {'id': current_user.id, 'data': com}
    emit('update_com', com1, to=room_id)
    current_room = room
    json = {'data': []}
    for player in room.players:
        json['data'].append(
            {'nickname': player.nickname, 'budget': player.budget})
    emit('update_players', json, to=room_id)
    # emit('update_decision') здесь передадим что то, что в последствии покажет решение игрока


@app.route('/delete_room/<room_id>')
def detele_room(room_id):
    room_id = int(room_id)
    global active_rooms
    print('')
    room = get_room(room_id)

    if room is None:
        print(f'room with id {room_id} not found')
        return redirect('/rooms')

    if room.stage != -1:
        print(f'room with id {room_id} in game')
        return redirect('/rooms')

    if room.players:
        print(f'room with id {room_id} not empty')
        return redirect('/rooms')

    print(f'deleting {room}')
    print(f'rooms before deleting: {active_rooms}')
    active_rooms.remove(room)
    db_sess = db_session.create_session()
    room_from_bd = db_sess.query(Rooms).get(room_id)
    db_sess.delete(room_from_bd)
    db_sess.commit()
    print(f'rooms before deleting: {active_rooms}')
    print('')

    return redirect('/rooms')


@socketIO.on('join')
def on_join(room):
    join_room(room)
    current_room = get_room(room)
    json = {'data': []}
    for player in current_room.players:
        json['data'].append(
            {'nickname': player.nickname, 'budget': player.budget})
    emit('update_players', json, to=room)
    com = {}
    for i in get_room(room).realty_list:
        com[i.name] = i.owner
    com1 = {'id': current_user.id, 'data': com}
    emit('update_com', com1, to=room)
    stonks = {'id': current_user.id, 'data': [
        {'short_name': i.short_name, 'cost': i.cost, 'stocks': get_room(room).get_player(current_user.id).stocks[i]} for
        i
        in get_room(room).get_player(current_user.id).stocks]}
    emit('update_bag', stonks, to=room)
    players = [len(get_room(room).players), len([i for i in get_room(room).players if i.ready])]
    emit('make_turn', players, to=room)
    update_money(room, {"id": current_user.id, "money": get_room(room).get_player(current_user.id).budget})


@socketIO.on('disconnect')
def disconnect():
    for room in active_rooms:

        room.leave_player(current_user.id)
        current_room = room
        json = {'data': []}
        for player in current_room.players:
            json['data'].append(
                {'nickname': player.nickname, 'budget': player.budget})
        emit('update_players', json, to=room)


@socketIO.on('leave')
def on_leave(room):
    print(room, 'leave socket')
    leave_room(room)
    user = current_user.id
    get_room(room).leave_player(user)
    current_room = get_room(room)
    json = {'data': []}
    for player in current_room.players:
        json['data'].append(
            {'nickname': player.nickname, 'budget': player.budget})
    emit('update_players', json, to=room)


@socketIO.on('sell')
def sell(json):
    print(json, 'sell socket')
    make_decision(json)
    # emit('', to=json['room'])


@socketIO.on('test')
def sell():
    print('test socket')


@socketIO.event
def add_message(json, room_id):
    get_room(room_id)
    room = '1'
    emit('new_message', json, to=room)


@socketIO.on('get_com_buy')
def get_com_buy(json):
    room = json['room_id']
    id = json['player_id']
    title = json['title']
    com = ''
    for i in get_room(room).realty_list:
         if i.name == title:
             com = i
    json = {
        'player_id': id,
        'room_id': room,
        'title': title,
        'des': 'des',
        'bonus': com.bonus,
        'cost': com.cost,
        'owner': com.owner,
        'count': com.realty_stock_quantity
    }

    emit('get_com_buy', json, to=room)


def get_room(room_id):
    for room in active_rooms:
        if room:
            if room.id == room_id:
                return room
    return None


def log(room_id, data):
    emit('log', data, to=room_id)


def add_friend(self_id, friend_id):
    user = User()
    db_sess = db_session.create_session()
    friends = db_sess.query(User).filter(User.id == self_id).split()[-1] + [str(friend_id)]
    user.friends = ','.join(friends)
    db_sess.commit()
    return True


def del_friend(self_id, friend_id):
    user = User()
    db_sess = db_session.create_session()
    friends = db_sess.query(User).filter(User.id == self_id).split()[-1]
    friends.remove(str(friend_id))
    user.friends = ','.join(friends)
    db_sess.commit()
    return True


if __name__ == '__main__':

    db_session.global_init("db/project_db.db")
    db_sess = db_session.create_session()

    rooms_from_db = db_sess.query(Rooms).all()
    for room_from_db in rooms_from_db:
        new_room = InGameRoom(room_from_db.id, room_from_db.title, room_from_db.data, room_from_db.players)
        active_rooms.append(new_room)

    port = int(os.environ.get("PORT", 3500))
    app.run(host='0.0.0.0', port=port, ssl_context='adhoc')

