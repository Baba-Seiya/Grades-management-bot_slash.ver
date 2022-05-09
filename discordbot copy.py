# インストールした discord.py を読み込む
import discord
import pickle
import asyncio
import re
from pyrsistent import b
import config
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
# MySQLdbのインポート
import MySQLdb

guild_ids = [int(config.GUILD_ID1),int(config.GUILD_ID2),int(config.GUILD_ID3)] # Put your server ID in this array.
 
# データベースへの接続とカーソルの生成
connection = MySQLdb.connect(
    host='localhost',
    user='root',
    passwd=config.PASS,
    db='python_db')
cursor = connection.cursor()

# 自分のBotのアクセストークンに置き換えてください
TOKEN = config.MY_TOKEN

# 接続に必要なオブジェクトを生成
client = discord.Client(intents=discord.Intents.all())
slash_client = SlashCommand(client,sync_commands=True)
#--------------------------------------------定義関数--------------------------------------------
#db関連の関数
def column_ser(chr):
    try:
        cursor.execute(f"SELECT * FROM {table} where {chr}")
        return True
    except MySQLdb._exceptions.OperationalError:
        return False
#matchのADをリセットする関数。
def clean_match(svid):
    cursor.execute(f"delete from matching where A_{svid} or D_{svid}")

#win lose dictを空にする関数
def clean(svid):
    global A
    global D
    A = []
    D = []

#選手の登録する際の関数
def regist(name, id, svid):
    #サーバーが登録されているか確認
    if not column_ser(f"{svid}_win"):
        #無かった場合追加する
        cursor.execute(f"ALTER TABLE {table} ADD {svid}_win int NULL, ADD {svid}_match int NULL, ADD {svid}_rate int NULL")
        cursor.execute(f"ALTER TABLE matching ADD A_{svid} bigint NULL, ADD D_{svid} bigint NULL")

    #その人が登録されているか確認
    cursor.execute(f"SELECT * FROM {table} where userID={id}")
    data = cursor
    for i in data:
        #見つかったらその人がこのサーバーに登録されているか確認する
        if i[1] == id:
            cursor.execute(f"SELECT userID, {svid}_win FROM {table} where userID={id}")
            for u in cursor:
                #None（未登録）だったら0を入れて登録する。
                if u[1] == None:
                    cursor.execute(f"update {table} set {svid}_win=0, {svid}_match=0, {svid}_rate=0 where userID={id}")
                    return "サーバーを追加登録しました"
            return "登録済みです"
        break
    else:
        #見つからなかったらその人とサーバーを登録する
        cursor.execute(f"insert into {table}(userName,userID,{svid}_win,{svid}_match,{svid}_rate) values(\"{name}\",{id},0,0,0)")
        return "ユーザを登録をしました"

    return "登録済みです"


#--------------------------変数置き場-------------------------
memberID = [["kame"]] #重複登録確認用ID置き場[[user.id,serverid,serverid....],[...]]
member = {} #キー=id,値=インスタンス名のdict  
instanceName = [] #インスタンス名の管理用 (表示名で登録 message.author)
memberNames = {} #キー=表示名, 値=id
A = [] #userIDが入る
D = []
serverList = []#各サーバーに対して[[serverid,[A],[D],…]のリスト  

table = "PlayerManager" #sqlデバック用

# カスタム絵文字
EmojiA = "🅰️"
EmojiD = "\N{Turtle}"
EmojiOK= "🆗"
EmojiW = "✅"
EmojiL = "❌"
EmojiC = "🚫"

#-----------------------discord.py event-----------------
# ---------------------起動時に動作する処理-----------------
@client.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される
    print('ログインしました')

#-------------------プログラムを終了する時に必要な動作------------------
@slash_client.slash(name="exit",description="botの終了。このコマンドまじで意味ないしリスクでしかない。なんなん？", guild_ids=guild_ids)
async def _slash_exit(ctx: SlashContext):
    await ctx.send(content="bye")
    # 保存を実行
    connection.commit()

    # 接続を閉じる
    connection.close()
    print("正常に終了しました")
    exit()

# ------------------スラッシュコマンドにより動作する処理------------
#選手の登録
@slash_client.slash(name="regist",description="選手の登録。戦績を記録をしたい人はまずこのコマンドを打ってください", guild_ids=guild_ids)
async def _slash_regist(ctx: SlashContext):
    name = str(ctx.author)
    id = int(ctx.author_id)
    svid =int(ctx.guild_id) 
    ans = regist(name,id,svid)
    connection.commit()
    await ctx.send(content=str(ans))

@slash_client.slash(name="regist_test",description="なんで作ったかわからん何が起きるの？",guild_ids=guild_ids)
async def _slash_regist_test(ctx: SlashContext):
    name = "testman"
    id = 1234567890
    svid ="serverid" 
    ans = regist(name,id,svid)
    connection.commit()
    await ctx.send(content=str(ans))

#戦績の表示
@slash_client.slash(name="score",description="戦績の一覧を表示します。勝ち負け数関係なく勝率でソートしてます。", guild_ids=guild_ids)
async def _slash_score(ctx: SlashContext):
    svid = int(ctx.guild_id)
    msg = ""
    if column_ser(f"{svid}_win"):
        cursor.execute(f"SELECT userName, userID, {svid}_win, {svid}_match, {svid}_rate FROM {table} where {svid}_win is not null")
        for i in cursor:
            #勝率を更新する 
            cursor.execute(f"update {table} set {svid}_rate={svid}_win/{svid}_match*100 where userID={i[1]} and {svid}_match >= 1")
        
        cursor.execute(f"SELECT userName, userID, {svid}_win, {svid}_match, {svid}_rate FROM {table} where {svid}_win is not null order by {svid}_rate desc")
        #ソートして表示
        x=1
        for i in cursor:
            msg += f"{x}. {i[0]} 勝率:{i[4]}% 勝ち数:{i[2]} 試合回数:{i[3]}\n"
            x += 1 
    connection.commit()
    await ctx.send(content=msg)
    
#boombot連携match
@slash_client.slash(name="match-b",description="boombotを使用して登録します。v.teamを打ったチャンネルで使用してください。技術力無くて最新のv.teamしか読み取れません。ごめんって", guild_ids=guild_ids)
async def _slash_matchb(ctx: SlashContext):
    channel = client.get_channel(ctx.channel.id)
    svid = int(ctx.guild_id) 
    content=f""
    msgList = await channel.history(limit=30).flatten() 
    for i in msgList:
        match_result = re.match(r"\*\*Information\*\*", i.content)
        if match_result:
            msgID = i.id
            break
        else:
            continue

    try:
        message = await channel.fetch_message(msgID) 
    except(UnboundLocalError):
        await message.channel.send("boombotの情報が読み取れませんでした。/match!b<messeageID>で指定してください。")
        return
    #正規表現にてユーザーidを抜き出す
    clean_match(svid)
    msg = message.content
    id_list = re.findall(r'@[\S]{1,18}',msg)
    x = round(len(id_list)/2)
    #Attackerに振り分ける処理
    content += "Attacer:\n"
    for i in range(x):
        id = id_list[i]
        cursor.execute(f"SELECT userName, userID FROM {table} where userID={id[1:]}")
        for i in cursor:
            name = str(i[0])
        cursor.execute(f"insert into matching(A_{svid}) values({id[1:]})")
        content += str(name) +"\n"

    #Defenderに振り分ける処理
    content += "Defender:\n"
    for i in range(x,len(id_list)):
        id = id_list[i]
        cursor.execute(f"SELECT userName, userID FROM {table} where userID={id[1:]}")
        for i in cursor:
            name = str(i[0])
        cursor.execute(f"insert into matching(D_{svid}) values({id[1:]})")
        content += str(name) + "\n"
    
        content += f"この内容で正しければ{EmojiOK}キャンセルする場合は{EmojiC}を押してください"
        connection.commit()
        msg = await ctx.send(content)
        await msg.add_reaction(EmojiOK)
        await msg.add_reaction(EmojiC)




@slash_client.slash(name="hello",description="デバックで使った奴。ハロー！", guild_ids=guild_ids)
async def _slash_hello(ctx: SlashContext):
    await ctx.send(content="Hello!")

@slash_client.slash(name="dbtest",description="デバックで使った奴。", guild_ids=guild_ids)
async def _slash_dbtest(ctx: SlashContext):
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    for i in rows:
        await ctx.send(content=str(i))
    

#---------------------リアクションがついた時の動作----------------------
@client.event
async def on_reaction_add(reaction, user):
    global serverList
    channel = client.get_channel(reaction.message.channel.id)
    svid = int(reaction.message.guild.id)
    if user.bot: #botの場合無視する
        return
    emoji =  reaction.emoji

    #完了した時の処理
    if emoji == EmojiOK:
        content = f"どっちが勝ちましたか?\n Attackerが勝った場合{EmojiW}　負けた場合{EmojiL}を押してください キャンセルは{EmojiC}"
        msg = await channel.send(content)
        await msg.add_reaction(EmojiW)
        await msg.add_reaction(EmojiL)
        await msg.add_reaction(EmojiC)
        
#勝敗登録  
    if emoji == EmojiW:
        cursor.execute(f"select A_{svid} from matching where A_{svid} is not null")
        A = cursor
        for i in A:
            cursor.execute(f"update PlayerManager set {svid}_win={svid}_win+1 where userID={i[0]}")
            cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
        
        cursor.execute(f"select D_{svid} from matching where D_{svid} is not null")
        D = cursor
        for i in D:
            cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")

        connection.commit()
        await channel.send('Attackerが勝ちとして記録しました。戦績を見る場合は!score')
    
    if emoji == EmojiL:
        cursor.execute(f"select A_{svid} from matching where A_{svid} is not null")
        A = cursor
        for i in A:
            cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
        
        cursor.execute(f"select D_{svid} from matching where D_{svid} is not null")
        D = cursor
        for i in D:
            cursor.execute(f"update PlayerManager set {svid}_win={svid}_win+1 where userID={i[0]}")
            cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
        connection.commit()
        await channel.send("Defenderが勝ちとして記録しました。戦績を見る場合は!score")


    if emoji == EmojiC:
        content = "キャンセルしました　!matchからやり直してください"
        await channel.send(content)
        clean_match(svid)

#memo
"""# ------------------メッセージ受信時に動作する処理------------
@client.event
async def on_message(message):
    global serverList
    global A
    global D
    global ADtable
    id_list = [] #boombot 連携にて使用　使い方忘れた
    svid = message.guild.id  #どのサーバーから来たか分かるように定義する。
    x = 0  #クラス変数が使えな勝ったので選手の数とする,選手の登録で使用
    channel = client.get_channel(message.channel.id)
    content=f""
    #boombot連動!match ID検索
    if message.content[:8] == "!match-b":
        if len(message.content) == 26:
            clean(svid)
            content = f""
            message = await channel.fetch_message(int(message.content[8:]))
    #正規表現にてユーザーidを抜き出す
    clean_match(svid)
    msg = message.content
    id_list = re.findall(r'@[\S]{1,18}',msg)
    x = round(len(id_list)/2)
    #Attackerに振り分ける処理
    content += "Attacer:\n"
    for i in range(x):
        id = id_list[i]
        cursor.execute(f"SELECT userName, userID FROM {table} where userID={id[1:]}")
        for i in cursor:
            name = str(i[0])
        cursor.execute(f"insert into {ADtable}(A_{svid}) values({id[1:]})")
        content += str(name) +"\n"

    #Defenderに振り分ける処理
    content += "Defender:\n"
    for i in range(x,len(id_list)):
        id = id_list[i]
        cursor.execute(f"SELECT userName, userID FROM {table} where userID={id[1:]}")
        for i in cursor:
            name = str(i[0])
        cursor.execute(f"insert into {ADtable}(D_{svid}) values({id[1:]})")
        content += str(name) + "\n"
    
        content += f"この内容で正しければ{EmojiOK}キャンセルする場合は{EmojiC}を押してください"
        connection.commit()
        msg = await message.channel.send(content)
        await msg.add_reaction(EmojiOK)
        await msg.add_reaction(EmojiC)"""
# Botの起動とDiscordサーバーへの接続
client.run(TOKEN)