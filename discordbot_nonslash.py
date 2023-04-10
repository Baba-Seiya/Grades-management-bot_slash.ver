# インストールした discord.py を読み込む
import discord
import asyncio
import re
import os
import config
from keep_alive import keep_alive
from discord.ext import commands
from discord_slash import SlashCommand

# MySQLdbのインポート
import MySQLdb

guild_ids = [int(os.environ["GUILD_ID1"]),int(os.environ["GUILD_ID2"]),int(os.environ["GUILD_ID3"])] # Put your server ID in this array.
 
# データベースへの接続とカーソルの生成
connection = MySQLdb.connect(
    host=os.environ["HOSTNAME"],
    user=os.environ["USER"],
    passwd=os.environ["PASS"],
    db=os.environ["DB"],
    charset="utf8mb4")
cursor = connection.cursor()

# 自分のBotのアクセストークンに置き換えてください
TOKEN = os.environ["MY_TOKEN"]

# 接続に必要なオブジェクトを生成
client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True)
#--------------------------------------------定義関数--------------------------------------------
#db関連の関数
def column_ser(chr): #カラムがあればT無ければFを返す関数。
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table} where {chr}")
        return True
    except MySQLdb._exceptions.OperationalError:
        return False

#db関連の関数
def column_ser_react(chr): #カラムがあればT無ければFを返す関数。
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM react where {chr}")
        return True
    except MySQLdb._exceptions.OperationalError:
        return False

#matchのADをリセットする関数。
def clean_match(svid):
    cursor = connection.cursor()
    try:
        cursor.execute(f"delete from matching where A_{svid} or D_{svid}")
        cursor.execute(f"delete from react where A_{svid} or D_{svid}")

    except:
        pass

#win lose dictを空にする関数
def clean(svid):
    global A
    global D
    A = []
    D = []

#選手の登録する際の関数
def regist(name, id, svid):
    cursor = connection.cursor()
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

#サーバーにその人の登録があるか確認する関数。(戻り値[結果TorF,人物名orエラー内容])
def server_serch(svid,id):
    cursor = connection.cursor()
    #サーバーが登録されているか確認
    if not column_ser(f"{svid}_win"):
        #無かったらエラーを返す
        return [False,"サーバーが登録されていません。"]
    lis = []
    #そのidがbotに登録されているか確認する
    cursor.execute(f"SELECT * FROM {table} where userID={id}")
    lis = cursor.fetchall()
    if not lis:
        return [False,"ユーザー登録がされていません。"]

    #そのidがサーバーが登録されているか確認する。
    lis = []
    cursor.execute(f"SELECT userID, {svid}_win FROM {table} where userID={id}")
    lis = cursor.fetchall()
    if lis[0][1] == None:
        return [False,"このサーバーに登録がありません。"]

    cursor.execute(f"SELECT * FROM {table} where userID={id}")
    for i in cursor:
        name = i[0]

    return [True,name]


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

# ------------------スラッシュコマンドにより動作する処理-----------
#-------------------これをコマンド式に戻す----------------------------
@client.event
async def on_message(ctx):
    #選手の登録
    if ctx.content == "!regist":
        name = str(ctx.author)
        id = int(ctx.author.id)
        svid =int(ctx.guild.id) 
        ans = str(regist(name,id,svid))
        connection.commit()
        embed = discord.Embed(title="**選手の登録**",color=discord.Colour.green())
        embed.add_field(name="現在の状態", value=ans, inline=False)
        embed.set_thumbnail(url=str(ctx.author.avatar_url))
        await ctx.channel.send(embed=embed)

    #戦績の表示
    if ctx.content == "!score":
        svid = int(ctx.guild.id)
        msg = "```"
        if column_ser(f"{svid}_win"):
            cursor = connection.cursor()
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
        msg += "```"
        embed = discord.Embed(title="**戦績の表示**",description=msg,color=discord.Colour.orange())

        await ctx.channel.send(embed=embed)
        
    #boombot連携match
    if ctx.content == "!match-b":
        cursor = connection.cursor()
        channel = client.get_channel(ctx.channel.id)
        svid = int(ctx.guild.id) 
        content=f""
        #メッセージを読みだす
        msgList = await channel.history(limit=50).flatten() 
        for i in msgList:
            for j in i.embeds:
                match_result = j.title 
                if match_result == "Attacker Side":
                    msgID = i.id
                    break
            else:
                continue
            break

        try:
            message = await channel.fetch_message(msgID) 
        except(UnboundLocalError):
            msg="boombotの情報が読み取れませんでした。/match-b<messeageID>で指定してください。"
            embed = discord.Embed(title="**エラー**",description=msg,color=discord.Colour.red())
            await ctx.channel.send(embed=embed)
            return
        
        #正規表現にてユーザーidを抜き出す
        clean_match(svid)
        msg = message.embeds
        id_list = re.findall(r'@[\S]{1,18}',msg[0].description)
        defender = re.findall(r'@[\S]{1,18}',msg[1].description)
        id_list.extend(defender)
        x = round(len(id_list)/2)
        #Attackerに振り分ける処理
        content += "Attacer:\n"
        for i in range(x):
            id = id_list[i]
            ans = server_serch(svid,id[1:])
            if ans[0]:
                #最終結果からmatchingテーブルを編集する。
                cursor.execute(f"insert into matching(A_{svid}) values({id[1:]})")
                content += str(ans[1]) +"\n"
                continue
            content += str(ans[1]) + "\n"

        #Defenderに振り分ける処理
        content += "Defender:\n"
        for i in range(x,len(id_list)):
            id = id_list[i]
            ans = server_serch(svid,id[1:])
            if ans[0]:
                #最終結果からmatchingテーブルを編集する。
                cursor.execute(f"insert into matching(D_{svid}) values({id[1:]})")
                content += str(ans[1]) + "\n"
                continue
            content += str(ans[1]) + "\n"

        mes = f"正しければ{EmojiOK}キャンセルする場合は{EmojiC}を押してください"
        connection.commit()

        embed = discord.Embed(title="選手の振り分け",description=content,color=discord.Colour.orange())
        embed.add_field(name="この内容でよろしいですか？",value=mes)

        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction(EmojiOK)
        await msg.add_reaction(EmojiC) 
        return

    #boombot連動!match ID検索
    if ctx.content[:8] == "!match-b":
        cursor = connection.cursor()
        channel = client.get_channel(ctx.channel.id)
        svid = int(ctx.guild.id) 
        content=f""
        if len(ctx.content) > 25:
            clean_match(svid)
            content = f""
            ctx = await channel.fetch_message(int(ctx.content[8:]))

            #正規表現にてユーザーidを抜き出す
            msg = ctx.embeds
            id_list = re.findall(r'@[\S]{1,18}',msg[0].description)
            defender = re.findall(r'@[\S]{1,18}',msg[1].description)
            id_list.extend(defender)
            x = round(len(id_list)/2)

        #Attackerに振り分ける処理
        content += "**Attacker:**\n"
        for i in range(x):
            id = id_list[i]
            ans = server_serch(svid,id[1:])
            if ans[0]:
                #最終結果からmatchingテーブルを編集する。
                cursor.execute(f"insert into matching(A_{svid}) values({id[1:]})")
                content += str(ans[1]) +"\n"
                continue
            content += str(ans[1]) + "\n"
        #Defenderに振り分ける処理
        content += "**Defender:**\n"
        for i in range(x,len(id_list)):
            id = id_list[i]
            ans = server_serch(svid,id[1:])
            if ans[0]:
                #最終結果からmatchingテーブルを編集する。
                cursor.execute(f"insert into matching(D_{svid}) values({id[1:]})")
                content += str(ans[1]) + "\n"
                continue
            content += str(ans[1]) + "\n"

        mes = f"この内容で正しければ{EmojiOK} キャンセルする場合は{EmojiC}を押してください"
        connection.commit()

        embed = discord.Embed(title="選手の振り分け",description=content,color=discord.Colour.orange())
        embed.add_field(name="この内容でよろしいですか？",value=mes)

        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction(EmojiOK)
        await msg.add_reaction(EmojiC) 
    
    #戦績の記録（手動メンションタイプ）
    if ctx.content == "!match":
        cursor = connection.cursor()
        svid = int(ctx.guild.id)
        #サーバーが登録されているか確認
        if not column_ser_react(f"A_{svid}"):
            #無かった場合追加する
            cursor.execute(f"ALTER TABLE react ADD A_{svid} bigint NULL, ADD D_{svid} bigint NULL")  
        content = f"{EmojiA} = Attacker   {EmojiD} = Defender を選択して、完了したら{EmojiOK}を押してください。キャンセルは{EmojiC}"
        embed = discord.Embed(title="**match**",description=content,color=discord.Colour.orange())
        connection.commit()
        msg = await ctx.channel.send(embed=embed)

        await msg.add_reaction(EmojiA)
        await msg.add_reaction(EmojiD)
        await msg.add_reaction(EmojiOK)
        await msg.add_reaction(EmojiC)
        clean_match(svid)

    #!call!<messageid>emoji　で指定したリアクションの人を呼ぶ。
    if ctx.content[:5] == "!call":
        emoji = ctx.content[24:]
        channel = client.get_channel(ctx.channel.id)
        msg =f"集合\n"
        flag = False #messegeidの指定があるかないかを判定するフラグ
        
        #messegeidの指定が無かった場合（例!call<emoji>）
        try:
            flag = ctx.content[6:11]
            int(flag)
            flag = False
        
        except (ValueError) :
            flag = True

        if flag :
            emoji = ctx.content[5:]
            #そのリアクションがついてるメッセージを読みだす
            msgList = await channel.history(limit=150).flatten() 
            
            for i in msgList:
                reactions = i.reactions

                for j in reactions:
                    #メッセージに対してその絵文字があるか確認
                    if j.emoji == emoji:
                        async for user in j.users():
                            if user.bot :
                                continue
                            msg += f"<@{int(user.id)}>\n"                                 
            embed = discord.Embed(title="**呼び出し**",description=msg,color=discord.Colour.blue())
            await channel.send(embed=embed)
            

        #messegeidの指定があった場合
        if len(ctx.content) > 17:
            ctx = await channel.fetch_message(int(ctx.content[5:24]))
            reaction = ctx.reactions
            msg =f"集合\n"
            #await channel.send(f"集合\n")
            for i in reaction:
                if i.emoji == emoji:
                    async for user in i.users():
                        if user.bot :
                            continue
                        msg += f"<@{int(user.id)}>\n"
                        #await channel.send(f"{user.mention}\n")
            embed = discord.Embed(title="**呼び出し**",description=msg,color=discord.Colour.blue())
            await channel.send(embed=embed)

    #help
    if ctx.content == "!help":
        content="""１．選手登録を行う
記録する選手はまず選手登録が必要になります。
!regist　と入力すると自動で入力した選手が登録されます

NEW!サーバー別に記録できるようになりましたNEW!
サーバー別に記録するようになったので別サーバーにて使用する際は!registをしてください。
○○を追加登録しました！　と表示されたらサーバー別登録完了です。

２.試合結果の登録(boom bot連動タイプ)
注意！（入力したテキストチャンネルチャンネルid とboom bot が同じテキストチャンネルにメッセージがある必要があります）
!match-b と入力するとboom botの最新の/valo teamの結果を参照してAttackerとDefenderを振り分けてくれます。
振り分けが正しければOKリアクションをしてください。
後は言われた通りやってください。

３．試合結果の表示
!score　と入力すると勝率順でソートした個人別成績が表示されます。

４．メッセージ、リアクション指定で一括メンション機能実装！！！
時間にルーズなゲーマーが多いため仕方なく実装しました。
!call<messegeid><メッセージについてる絵文字>（例）/call!968048735617695744🐑
↑を使用するとそのメッセージについてる指定したリアクションに反応した人を一斉メンション出来ます。"""
        embed = discord.Embed(title="**Grades management bot help v.1.8.4**",color=discord.Colour.orange(),)
        embed.add_field(
            name="１．選手登録を行う",
            value="""`!regist`
            ```記録する選手はまず選手登録が必要になります。!registと入力すると自動で入力した選手が登録されます```"""
            ,inline=False)
        embed.add_field(
            name="NEW!サーバー別に記録できるようになりましたNEW!",
            value="```サーバー別に記録するようになったので別サーバーにて使用する際は!registをしてください。○○を追加登録しました！と表示されたらサーバー別登録完了です。```",
            inline=False)
        embed.add_field(
            name="２.１試合結果の登録(boom bot連動タイプ)",
            value="""`!match-b`
            ```!match-bと入力するとboom botの最新の./valo teamの結果を参照してAttackerとDefenderを振り分けてくれます。振り分けが正しければOKリアクションをしてください。後は言われた通りやってください。(!match-b‹messege id›でメッセージIDを指定することも可能)``````注意！（入力したテキストチャンネルチャンネルid とboom bot が同じテキストチャンネルにメッセージがある必要があります）```""",
            inline=False)
        embed.add_field(
            name="２.２試合結果の登録(リアクションタイプ)",
            value="""`!match`
            ```!matchと入力すると、メッセージと共にリアクションが追加され、メッセージの指示に従いリアクションを追加してチーム分けをします。振り分けが終わったらOKリアクションを押して、後は言われたとおりにやってください。```""",
            inline=False)
        embed.add_field(
            name="３．試合結果の表示",
            value="""`!score`
            ```!scoreと入力すると勝率順でソートした個人別成績が表示されます。```""",
            inline=False)
        embed.add_field(
            name="NEW!! メッセージ、リアクション指定で一括メンション機能実装！！！",
            value="""`!call`
            ```時間にルーズなゲーマーが多いため仕方なく実装しました。
!call<messegeid><メッセージについてる絵文字>（例）/call!968048735617695744🐑
↑を使用するとそのメッセージについてる指定したリアクションに反応した人を一斉メンション出来ます。
NEW！！　/call<絵文字>直近のその絵文字がついてるメッセージのリアクションをメンションするようになりました```""",
            inline=False)
        await ctx.channel.send(embed=embed)

#---------------------リアクションがついた時の動作----------------------
@client.event
async def on_reaction_add(reaction, user):
    global serverList
    userid = int(user.id)
    channel = client.get_channel(reaction.message.channel.id)
    svid = int(reaction.message.guild.id)
    reactflag = False
    cursor = connection.cursor()

    #そのメッセージのリアクション
    reactions = reaction.message.reactions
    
    #ひとつ前のリアクションを読み取ってリアクションタイプかを判定する。
    msgList = await channel.history(limit=2).flatten()
    for i in msgList:
        reactions_before = i.reactions

    if user.bot: #botの場合無視する
        return
    emoji =  reaction.emoji

    #完了した時の処理（リアクションタイプ時振り分け処理）
    if emoji == EmojiOK:
        #リアクションタイプかどうかを判定する
        for i in reactions:
            if i.emoji == EmojiA or i.emoji ==  EmojiD:
                reactflag = True
                break
        
        #リアクションタイプだった場合
        if reactflag:
            for i in reactions:
                #絵文字がAの場合
                if i.emoji == EmojiA:
                    
                    #userIDをリアクションから抜き出す
                    async for user in i.users():
                        if user.bot :
                            continue
                        userid = int(user.id)                    

                        #reactテーブルのA_svidに追加する。
                        cursor.execute(f"INSERT INTO react (A_{svid}) values({userid})")
                        connection.commit()

                if i.emoji == EmojiD:
                    
                    #userIDをリアクションから抜き出す
                    async for user in i.users():
                        if user.bot :
                            continue
                        userid = int(user.id)     

                        #reactテーブルのA_svidに追加する。
                        cursor.execute(f"INSERT INTO react (D_{svid}) values({userid})")
                        connection.commit()
            
        content = f"どっちが勝ちましたか?\n Attackerが勝った場合{EmojiW} 負けた場合{EmojiL}を押してください キャンセルは{EmojiC}"
        embed = discord.Embed(title="**勝敗登録**",description=content,color=discord.Colour.orange())
        msg = await channel.send(embed=embed)
        await msg.add_reaction(EmojiW)
        await msg.add_reaction(EmojiL)
        await msg.add_reaction(EmojiC)
        
#勝敗登録  
    #勝った時
    if emoji == EmojiW: 
        #リアクションタイプかそうでないかを判別するフラグ
        reactflag = False

        #リアクションの中にリアクションタイプで使用する絵文字があったらフラグを立てる
        for i in reactions_before:
            if i.emoji == EmojiA or i.emoji ==  EmojiD:
                reactflag = True

        #if 内はリアクションタイプの時(A側の登録処理)
        if reactflag : 
            cursor = connection.cursor()
            #reactテーブルからそのサーバーのAカラムからNULL以外を取り出す、
            cursor.execute(f"select A_{svid} from react where A_{svid} is not null")
            A = cursor
            for i in A:
                #PlayerManagaerの更新
                try:
                    cursor.execute(f"update PlayerManager set {svid}_win={svid}_win+1 where userID={i[0]}")
                    cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
                    connection.commit()
                except:
                    content = "登録してる人がいません。!registからユーザー登録してください。!helpからヘルプが見れます。"
                    embed = discord.Embed(title="**エラー**",description=content,color=discord.Colour.red())    
                    await channel.send(embed=embed)
                    return

            #D側の登録処理
            cursor.execute(f"select D_{svid} from react where D_{svid} is not null")
            D = cursor
            for i in D:
                cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
                connection.commit()
       
        #match-bの時の登録処理
        else:
            cursor = connection.cursor()
            #match-bの時の登録処理
            #matchingテーブルからそのサーバーのAカラムからNULL以外を取り出す、
            cursor.execute(f"select A_{svid} from matching where A_{svid} is not null")
            A = cursor
            for i in A:
                #PlayerManagaerの更新
                try:
                    cursor.execute(f"update PlayerManager set {svid}_win={svid}_win+1 where userID={i[0]}")
                    cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
                except:
                    content = "登録してる人がいません。!registからユーザー登録してください。!helpからヘルプが見れます。"
                    embed = discord.Embed(title="**エラー**",description=content,color=discord.Colour.red())    
                    await channel.send(embed=embed)
                    return

            #D側の登録処理
            cursor.execute(f"select D_{svid} from matching where D_{svid} is not null")
            D = cursor
            for i in D:
                cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
        
        connection.commit()
        embed = discord.Embed(title="**勝敗結果**",description='Attackerが勝ちとして記録しました。戦績を見る場合は!score',color=discord.Colour.orange())
        await channel.send(embed=embed)
        clean_match(svid)
    
    #負けた時
    if emoji == EmojiL:
        #リアクションタイプかそうでないかを判別するフラグ
        reactflag = False

        #リアクションの中にリアクションタイプで使用する絵文字があったらフラグを立てる
        for i in reactions_before:
            if i.emoji == EmojiA or i.emoji ==  EmojiD:
                reactflag = True

        #if 内はリアクションタイプの時(A側の登録処理)
        if reactflag : 
            cursor = connection.cursor()
            #reactテーブルからそのサーバーのAカラムからNULL以外を取り出す、
            cursor.execute(f"select A_{svid} from react where A_{svid} is not null")
            A = cursor
            for i in A:
                #PlayerManagaerの更新
                try:
                    cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
                    connection.commit()
                except:
                    content = "登録してる人がいません。!registからユーザー登録してください。!helpからヘルプが見れます。"
                    embed = discord.Embed(title="**エラー**",description=content,color=discord.Colour.red())    
                    await channel.send(embed=embed)
                    return                
            #D側の登録処理
            cursor.execute(f"select D_{svid} from react where D_{svid} is not null")
            D = cursor
            for i in D:
                cursor.execute(f"update PlayerManager set {svid}_win={svid}_win+1 where userID={i[0]}")
                cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
                connection.commit()


        #match-bの時の登録処理
        else:
            cursor = connection.cursor()
            #match-bの時の登録処理
            #matchingテーブルからそのサーバーのAカラムからNULL以外を取り出す、
            cursor.execute(f"select A_{svid} from matching where A_{svid} is not null")
            A = cursor
            for i in A:
                #PlayerManagaerの更新
                try:
                    cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
                except:
                    content = "登録してる人がいません。!registからユーザー登録してください。!helpからヘルプが見れます。"
                    embed = discord.Embed(title="**エラー**",description=content,color=discord.Colour.red())    
                    await channel.send(embed=embed)
                    return

            #D側の登録処理
            cursor.execute(f"select D_{svid} from matching where D_{svid} is not null")
            D = cursor
            for i in D:
                cursor.execute(f"update PlayerManager set {svid}_win={svid}_win+1 where userID={i[0]}")
                cursor.execute(f"update PlayerManager set {svid}_match={svid}_match+1 where userID={i[0]}")
        
        connection.commit()
        embed = discord.Embed(title="**勝敗結果**",description='Defenderが勝ちとして記録しました。戦績を見る場合は!score',color=discord.Colour.orange())
        await channel.send(embed=embed)
        clean_match(svid)

    if emoji == EmojiC:
        content = "キャンセルしました　!matchからやり直してください"
        embed = discord.Embed(title="**エラー**",description=content,color=discord.Colour.red())
        await channel.send(embed=embed)
        clean_match(svid)

# Botの起動とDiscordサーバーへの接続
keep_alive()
client.run(TOKEN)