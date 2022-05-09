# MySQLdbのインポート
from distutils.command.config import config
import MySQLdb
import config
# データベースへの接続とカーソルの生成
connection = MySQLdb.connect(
    host='localhost',
    user='root',
    passwd=config.PASS,
    db='python_db')
cursor = connection.cursor()
table = "PlayerManager"
id = 588371754737729543
# ここに実行したいコードを入力します
try:
    cursor.execute("SELECT userID, 694718084078108693_win FROM PlayerManager where userID=424207709043425281;")
    for row in cursor:
        print(row)
    if row[1] == 1234567890:
        print("一致")
except MySQLdb._exceptions.OperationalError:
    print("karamuga nai")


# 保存を実行
connection.commit()
 
# 接続を閉じる
connection.close()