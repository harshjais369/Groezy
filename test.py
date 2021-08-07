from instagrapi import Client

# cl = Client()
# cl.login("nidhi_singh_4141", "ig0123")
#
# user_id = cl.user_id_from_username("harshjais369")
# print(cl.user_info(user_id).json())

# open('tmp/dump_sessionId.txt', 'w').close()
#
r = open('tmp/dump_settings.json', 'r').read()
f = open('tmp/dump_settings.json', 'w')
f.write(r.replace('\'', '\"'))
f.close()
#
# if not f.read(1):
#     print('File is empty!')
# else:
#     f = open('tmp/dump_sessionId.txt')
#     print('File has content:\n\n' + f.read())

# import mysql.connector
#
# mydb = mysql.connector.connect(
#     host="148.163.102.242",
#     user="fastdon2_groezy",
#     password="Whyitellu$369",
#     database="fastdon2_gz_db"
# )
#
# my_cursor = mydb.cursor()
# my_cursor.execute("""UPDATE gz_ig_users SET name = "nnn" WHERE id = 15""")
# mydb.commit()
# print(my_cursor.rowcount)
# for db in my_cursor:
#     print(db)


