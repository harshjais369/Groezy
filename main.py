import ast
import json
from random import randrange
from flask import Flask, request
import mysql.connector
from werkzeug.exceptions import abort
from instagrapi import Client
from instagrapi.exceptions import *

app = Flask(__name__)

cred_dict = json.loads(open('tmp/cred.json').read())
rand_index = randrange(len(cred_dict['cred']))
user_dict = cred_dict['cred'][rand_index]

P_SETTINGS = user_dict['session_id'].replace('\'', '\"').replace('True', 'true')
USERNAME = user_dict['username']
PSK = user_dict['psk']


def setup_db():
    try:
        db = mysql.connector.connect(
            host=cred_dict['mysql_cred']['host'],
            user=cred_dict['mysql_cred']['user'],
            password=cred_dict['mysql_cred']['psk'],
            database=cred_dict['mysql_cred']['db']
        )
        return db
    except:
        return None


def do_login(with_session, db1=None, user_uid=None, s_id=None, username=None, psk=None):
    cl = None
    cur1 = None
    if db1 is not None:
        cur1 = db1.cursor()
    try:
        if with_session:
            cl = Client(ast.literal_eval(s_id))
            cl.get_timeline_feed()
            # print("Logged in with Session")
        else:
            try:
                cl = Client()
                if not cl.login(username, psk):
                    cl = None
            except UserNotFound:
                cl = 3
            except BadPassword:
                cl = 4
            except Exception as e:
                cl = None
                if "username you entered doesn't" in str(e):
                    cl = 3
    except Exception as e:
        print(e)
        try:
            # Login failed using Session ID ----
            cur1.execute("""SELECT username, password FROM gz_ig_users WHERE id = %s""" % user_uid)
            ff = cur1.fetchall()
            if not ff:
                cl = None
            else:
                username = ff[0][0]
                psk = ff[0][1]
                cl = Client()
                if cl.login(username, psk):
                    cur1.execute("""UPDATE gz_ig_users SET session_id = "%s" WHERE id = %s""" % (
                        str(cl.get_settings()), user_uid))
                    db1.commit()
                    # if cur1.rowcount != 1:
                    #     print("Not updated - Session ID")
                    # else:
                    #     print("Updated")
                else:
                    print("Login failed with cred.")
                    cl = None
        except Exception as e:
            print(e)
            cl = None
    return cl


def init():
    cl = None
    try:
        if P_SETTINGS != '':
            cl = Client(json.loads(P_SETTINGS))
            # print("Logged in with Session")
        else:
            # Session string is empty! ----
            cl = Client()
            if cl.login(USERNAME, PSK):
                write_session_cred(cl.get_settings())
            else:
                cl = None
    except:
        try:
            # Login failed using Session ID ----
            cl = Client()
            if cl.login(USERNAME, PSK):
                write_session_cred(cl.get_settings())
            else:
                cl = None
        except:
            cl = None
    return cl


def write_session_cred(d):
    cred_dict['cred'][rand_index]['session_id'] = str(d)
    fn = open('tmp/cred.json', 'w')
    fn.write(str(json.dumps(cred_dict)))
    fn.close()


@app.route('/')
def index():
    abort(401)


@app.route('/auth', methods=['POST'])
def auth_ig_user():
    if 'username' not in request.form or 'psk' not in request.form:
        return '{"status": 5}'
    username = str(request.form['username'])
    psk = str(request.form['psk'])
    if username == "" or psk == "":
        return '{"status": 5}'
    cl = do_login(with_session=False, username=username, psk=psk)
    if cl is None:
        return '{"status": 22}'
    elif cl == 3:
        return '{"status": 3}'
    elif cl == 4:
        return '{"status": 4}'
    user_id = cl.user_id_from_username(username)
    user_info = cl.user_info(user_id).dict()
    ret_data = '{"status": 1, "data": {"pk": "%s", "name": "%s", "session_id": "%s", "profile_pic": "%s", ' \
               '"followers_count": "%s"}}' % (str(user_id), user_info['full_name'], str(cl.get_settings()),
                                              user_info['profile_pic_url'], user_info['follower_count'])
    return ret_data


@app.route('/login/<int:gz_ig_users_id>')
def login_ig_user(gz_ig_users_id):
    db = setup_db()
    if db is None:
        return '{"status": 2}'
    my_cursor = db.cursor()
    try:
        my_cursor.execute("""SELECT username, session_id FROM gz_ig_users WHERE id = %s""" % gz_ig_users_id)
        ff = my_cursor.fetchall()
        if not ff:
            return '{"status": 3}'
        username = ff[0][0]
        session_id = ff[0][1]
        cl = do_login(with_session=True, db1=db, user_uid=gz_ig_users_id, s_id=session_id)
        if cl is None:
            return '{"status": 22}'
        user_id = cl.user_id_from_username(username)
        user_info = cl.user_info(user_id).dict()
        try:
            my_cursor.execute("""UPDATE gz_ig_users SET name = "%s", profile_pic = "%s", followers_count = "%s"
            WHERE id = %s""" % (user_info['full_name'], user_info['profile_pic_url'], user_info['follower_count'],
                                gz_ig_users_id))
            db.commit()
            return '{"status": 1}'
        except:
            return '{"status": 12}'
    except:
        return '{"status": 2}'


@app.route('/user/<username>')
def func_users(username):
    cl = init()
    if cl is None:
        return '{"status": 2}'
    try:
        user_id = cl.user_id_from_username(username)
        return cl.user_info(user_id).json()
    except UserNotFound:
        return '{"status": 3}'
    except:
        return '{"status": 2}'


@app.route('/posts/<username>')
def func_posts(username):
    cl = init()
    if cl is None:
        return '{"status": 2}'
    try:
        user_id = cl.user_id_from_username(username)
        user_posts = cl.user_medias(user_id, 80)
        ret_data = []
        range_int = 0
        i = -1
        while range_int <= 50:
            i += 1
            if len(user_posts) < 80:
                if i == len(user_posts):
                    break
            elif i == 80:
                break
            try:
                post_dict = json.loads(user_posts[i].json())
                if int(post_dict['media_type']) != 1:
                    continue
                ret_data.append(
                    {"media_id": str(post_dict['pk']), "thumbnail_url": str(post_dict['thumbnail_url']),
                     "like_count": str(post_dict['like_count'])}
                )
            except:
                pass
            range_int += 1
        ret_dict = {"status": 1, "posts": ret_data}
        return str(ret_dict).replace('\'', '\"')
    except UserNotFound:
        return '{"status": 3}'
    except:
        return '{"status": 2}'


@app.route('/like/<media_id>', methods=['POST'])
def func_like(media_id):
    db = setup_db()
    if db is None:
        return '{"status": 2}'
    my_cursor = db.cursor()
    if 'id' not in request.form:
        return '{"status": 5}'
    gz_ig_users_id = str(request.form['id'])
    if gz_ig_users_id == "":
        return '{"status": 5}'
    try:
        my_cursor.execute("""SELECT session_id FROM gz_ig_users WHERE id = %s""" % gz_ig_users_id)
        ff = my_cursor.fetchall()
        if not ff:
            return '{"status": 3}'
        session_id = ff[0][0]
        cl = do_login(with_session=True, db1=db, user_uid=gz_ig_users_id, s_id=session_id)
        if cl is None:
            return '{"status": 22}'
        if cl.media_like(media_id):
            return '{"status": 1}'
        return '{"status": 0}'
    except Exception as e:
        print(e)
        return '{"status": 2}'


@app.route('/follow/<pk>', methods=['POST'])
def func_follow(pk):
    db = setup_db()
    if db is None:
        return '{"status": 2}'
    my_cursor = db.cursor()
    if 'id' not in request.form:
        return '{"status": 5}'
    gz_ig_users_id = str(request.form['id'])
    if gz_ig_users_id == "":
        return '{"status": 5}'
    try:
        my_cursor.execute("""SELECT session_id FROM gz_ig_users WHERE id = %s""" % gz_ig_users_id)
        ff = my_cursor.fetchall()
        if not ff:
            return '{"status": 3}'
        session_id = ff[0][0]
        cl = do_login(with_session=True, db1=db, user_uid=gz_ig_users_id, s_id=session_id)
        if cl is None:
            return '{"status": 22}'
        try:
            ig_user_id = int(pk)
            if cl.user_follow(ig_user_id):
                return '{"status": 1}'
            return '{"status": 0}'
        except ValueError:
            # Incorrect Instagram user ID
            return '{"status": 4}'
    except Exception as e:
        print(e)
        return '{"status": 2}'


if __name__ == '__main__':
    app.run(debug=True)
