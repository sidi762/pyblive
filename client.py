# -*- coding: utf-8 -*-
# Sidi Liang, Weihao Lee, 2020

import asyncio
import blivedm
import pyttsx3
import pyttsx3.drivers
# MacOS System please import nsss
import pyttsx3.drivers.nsss
# Windows System please import sapi5
# import pyttsx3.drivers.sapi5
import json
import aiohttp
import threading
import vlc
import os
import getpass
from multiprocessing import Process

version = "2.3"
versionStatus = "beta 8"
build = 30

vlcInstance = vlc.Instance()
mediaPlayer = vlc.MediaPlayer(vlcInstance)
songList = []
standbyList = []
songIndex = 0
standbyIndex = 0
lastPopularity = 0
highestPopularity = 0
income = 0
inStandByMode = 0
neteasePhone = 0
neteasePasswd = 0
roomid = 0
#server = "http://127.0.0.1:3000"
server = "http://kery.fgprc.org:3000"

#Development Note
#VLC MediaPlayer State
#{0: 'NothingSpecial',
# 1: 'Opening',
# 2: 'Buffering',
# 3: 'Playing',
# 4: 'Paused',
# 5: 'Stopped',
# 6: 'Ended',
# 7: 'Error'}
#
#Bug record:
#圆周率之歌 葛平

def text2SpeechProcess(content):
    ttsEngine = pyttsx3.init()
    ttsEngine.say(content)
    ttsEngine.runAndWait()

async def text2SpeechInProcess(content):
    ttsProcess = Process(target=text2SpeechProcess,args=(content,))
    ttsProcess.start()
    return
    
async def text2Speech(content):
    ttsEngine = pyttsx3.init()
    ttsEngine.say(content)
    ttsEngine.runAndWait()
    return

def listenKeyboard(loop):
    global songIndex
    global lastPopularity
    global inStandByMode
    asyncio.set_event_loop(loop)
    while True:
        try:
            keyboardLogic(loop)
        except:
            print("Error, skipping")
            
def keyboardLogic(loop):
    i = input("> ")
    if i == "test":
        print("Input detected")
    elif i == "status":
        print("当前人气值: " + str(lastPopularity))
    elif i == "debug":
        print("inStandByMode:" + str(inStandByMode))
        print("songIndex:" + str(songIndex))
        print("standbyIndex:" + str(standbyIndex))
        print("player status: " + str(mediaPlayer.get_status()))
    elif i == "pause":
        mediaPlayer.pause()
    elif i == "play":
        mediaPlayer.play()
    elif i == "stop":
        mediaPlayer.stop()
    elif i == "next":
        if songIndex >= len(songList):
            mediaPlayer.stop()
            print("This is the last song")
        else:
            setSong(songIndex)
    elif i == "list" or i == "ls":
        showRemainingSongList(songList)
    elif i == "full list":
        showFullSongList(songList)
    elif i[0:8] == "standby ":
        if i[8:12] == "add ":
            searchTask = asyncio.ensure_future(searchSong(i[12:]))
            loop.run_until_complete(searchTask)
            song = searchTask.result()
            if song:
                addingTask = asyncio.ensure_future(addToList(song, standbyList, 1))
                loop.run_until_complete(addingTask)
            else:
                print("Cannot add to standby list: Song not found")
        elif i[8:] == "list" or i[8:] == "ls":
            showRemainingSongList(standbyList, standbyIndex)
        elif i[8:] == "full list":
            showFullSongList(standbyList, standbyIndex)
        elif i[8:] == "next":
            mediaPlayer.stop()
        elif i[8:15] == "remove ":
            try:
                songToBeRemoved = int(i[8:]) - 1 #从1开始数
                standbyList.pop(songToBeRemoved)
            except:
                print("Error: invalid arguments")
        elif i[8:15] == "import ":
            try:
                importFromFile(i[15:])
            except:
                print("Import error: invalid file " + i[15:])
        else:
            print("Error: command not found")
   
    elif i[0:5] == "swap " and i[6] == " ":
        try:
            swap1 = int(i[7]) - 1 #从1开始数
            swap2 = int(i[5]) - 1
            if swap1 <= len(songList) and swap2 <= len(songList):
                tmp = songList[swap1]
                songList[swap1] = songList[swap2]
                songList[swap2] = tmp
            else:
                print("swap Error: Out of range")
        except:
            print("Error: invalid arguments")
        
    elif i == "clear":
        os.system("clear") #macOS, linux
    elif i == "cls":
        os.system("cls") #Windows
    elif i == "help":
        printHelp()
    elif i == "version" or i == "v":
        print(version  + " " + versionStatus + " build " + str(build))
    elif i == "":
        print(" ")
    elif i[0:7] == "remove ":
        try:
            songToBeRemoved = int(i[7:]) - 1 #从1开始数
            songList.pop(songToBeRemoved)
        except:
            print("Error: invalid arguments")
    elif i == "quit" or i == "exit":
        print("     Highest popularity: " + str(highestPopularity))
        print("     Total income: " + str(income))
        print("     Quitting, Good bye")
        os._exit(0)
    elif i[0:3] == "say":
        ttsProcess = Process(target=text2SpeechProcess,args=(i[4:],))
        ttsProcess.start()
    else:
        print("Error: command not found")
    

def mediaControlLoop(loop):
    global songIndex
    global standbyIndex
    global inStandByMode
    asyncio.set_event_loop(loop)
    while True:
        if songIndex < len(songList): #进入点歌模式
            if inStandByMode == 1:
                inStandByMode = 0
                mediaPlayer.stop()#立即切歌/不立即切歌
                print("     Stopping standby mode")

        if mediaPlayer.get_state() == 0 or mediaPlayer.get_state() == 5:
            if songIndex < len(songList):
                #点歌列表有歌
                print("     Not playing, now starting")
                inStandByMode = 0
                setSong(songIndex)
            elif standbyIndex < len(standbyList):
                #空闲列表有歌
                print("     Not playing, now starting standby")
                inStandByMode = 1
                setStandbySong(standbyIndex)

        if mediaPlayer.get_state() == 6:
            if inStandByMode:
                if standbyIndex < len(standbyList):
                    #空闲列表切歌
                    setStandbySong(standbyIndex)
                elif standbyIndex >= len(standbyList):
                    #空闲列表完成
                    #mediaPlayer.stop()
                    standbyIndex = 0
                    setStandbySong(standbyIndex)
                    print("     Standby list finished, looping")
            elif inStandByMode == 0:
                if songIndex < len(songList):
                    #点歌列表切歌
                    setSong(songIndex)
                elif songIndex >= len(songList):
                    #点歌列表完成
                    if len(standbyList):
                        #空闲列表有歌，进入空闲模式
                        inStandByMode = 1
                    elif not len(standbyList):
                        #空闲列表无歌
                        mediaPlayer.stop()
                        print("     Song list finished")

    return

def printHelp():
    print("Usage:")
    print("     say CONTENT: say anything you want")
    print("     status: show current popularity")
    print("     play: start playing music list")
    print("     pause: pause music")
    print("     stop: stop music list")
    print("     next: switch to next music")
    print("     list(ls): show list of not played music")
    print("     full list: show full list of music")
    print("     remove: remove a music in the list")
    print("     ")
    print("     standby add: add to standby list")
    print("     standby import FILE: import to standby list from file")
    print("     standby list(ls): show list of not played music in standby list")
    print("     standby full list: show full list of standby music")
    print("     standby remove: remove a music in standby list")
    print("     clear(macOS, linux): clear screen")
    print("     cls(Windows): clear screen")
    print("     help: show help message")
    print("     quit(exit): quit the program")

def importFromFile(file, list=standbyList):
    importFile = open(file)
    for line in importFile.readlines():                         
        for index in range(len(line)):
            if line[index] == "#":
                line = line[0:index]
                break
        
        line = line.strip() #去掉每行头尾空白  
        if line == "":
            continue
        searchTask = asyncio.ensure_future(searchSong(line))
        asyncio.get_event_loop().run_until_complete(searchTask)
        song = searchTask.result()
        if song:
            addingTask = asyncio.ensure_future(addToList(song, standbyList, 1))
            asyncio.get_event_loop().run_until_complete(addingTask)
        else:
            print("Cannot add to standby list: Song not found")
    
    return
    

def setSong(index):
    global songIndex
    urlResult = 0
    searchTasks = [asyncio.ensure_future(searchSongUrl(songList[index][1]))]
    asyncio.get_event_loop().run_until_complete(asyncio.wait(searchTasks))
    urlResult = searchTasks[0].result()
    if urlResult:
        mediaPlayer.set_mrl(urlResult)
        mediaPlayer.play()
        outputSongList = open('now_playing.txt', mode='w+',encoding='utf-8')
        print("正在播放： " + songList[index][0] + "  -  " + songList[index][2], file=outputSongList)
        outputSongList.close()
        print("     playing " + songList[index][0])
    else:
        print("     Failed: Song cannot be played")
        #pyttsx3.speak("很抱歉，由于出现了一些错误，此歌曲播放失败")
        speechTask = asyncio.ensure_future(text2SpeechInProcess("很抱歉，由于出现了一些错误，此歌曲播放失败"))
        asyncio.get_event_loop().run_until_complete(speechTask)
    songIndex = index + 1
    return

def setStandbySong(index):
    global standbyIndex
    urlResult = 0
    searchTasks = [asyncio.ensure_future(searchSongUrl(standbyList[index][1]))]
    asyncio.get_event_loop().run_until_complete(asyncio.wait(searchTasks))
    urlResult = searchTasks[0].result()
    if urlResult:
        mediaPlayer.set_mrl(urlResult)
        mediaPlayer.play()
        outputSongList = open('now_playing.txt', mode='w+', encoding='utf-8')
        print("正在播放： " + standbyList[index][0] + "   -   " + standbyList[index][2], file=outputSongList)
        outputSongList.close()
        print("     Standby playing " + standbyList[index][0])
    else:
        print("     Failed: Song cannot be played")
    standbyIndex = index + 1
    return

def showFullSongList(targetList, index=songIndex):
    if len(targetList) == 0:
        print("     List Empty")
    else:
        print("     Current Song: " + targetList[index - 1][0])
        print("     Full List: ")
        for song in targetList:
            print("     " + song[0])
    return

def showRemainingSongList(targetList, index=songIndex):
    if len(targetList) == 0:
        print("     List Empty")
    else:
        print("     Current Song: " + targetList[index - 1][0])
        print("     Remaining List: ")
        if songIndex >= len(targetList) - 1:
            print("     List Empty")
        else:
            for song in targetList[index:]:
                print("     " + song[0])
    return

async def listenTest():
    while True:
        i = input("> ")
        await searchSong(i)

async def fetch(session, url, params):
    async with session.get(url, params=params) as response:
        return await response.text()

async def post(session, url, params):
    async with session.post(url, data=params) as response:
        return await response.text()

async def phoneLogin(phone,passw):
    params = {'phone':phone, "password":passw}
    async with aiohttp.ClientSession() as session:
        result = await post(session, server + '/login/cellphone', params)
        return
        
async def refreshLogin():
    while True:
        await phoneLogin(neteasePhone, neteasePasswd)
        print("Login refreshed!")
        await asyncio.sleep(1200)
    return

async def searchSong(song):
    params = {'keywords': song}
    async with aiohttp.ClientSession() as session:
        jsonData = await fetch(session, server + '/search', params)
        #print(jsonData)
        data = json.loads(jsonData)
        allResults = data["result"]
        if allResults["songCount"] != 0:
            topResult = allResults["songs"][0]
            artistsResult = topResult["artists"][0]
            #print(topResult[0])
            #urlResult = await searchSongUrl(topResult["id"]) #Moved before the song being played as the url will expire
            return [topResult["name"], topResult["id"], artistsResult["name"]]
        else:
           return 0

async def searchSongUrl(id):
    params = {'id': id}
    async with aiohttp.ClientSession() as session:
        jsonData = await fetch(session, server + '/song/url', params)
        #print(jsonData)
        data = json.loads(jsonData)
        dataUrl = data["data"][0]["url"]
        return dataUrl

async def addToList(song, targetList, mode=0):
        if mode == 0:
            songList.append(song)
            print("Song " + song[0] + " added to the song list")
            await text2Speech("点歌成功, " + song[0] + "已添加到点歌列表")
        elif mode == 1:
            standbyList.append(song)
            print("Song " + song[0] + " added to the standby list")

class MyBLiveClient(blivedm.BLiveClient):

    # 自定义handler
    _COMMAND_HANDLERS = blivedm.BLiveClient._COMMAND_HANDLERS.copy()


    async def __on_vip_enter(self, command):
        #print(command)
        print("vip " + command["data"]["uname"] + " 进入直播间")
        await text2Speech("欢迎" + command["data"]["uname"] + "进入直播间")
    _COMMAND_HANDLERS['WELCOME'] = __on_vip_enter  #老爷入场

    async def _on_receive_popularity(self, popularity: int):
        global lastPopularity
        global highestPopularity
        if popularity != lastPopularity:
            print(f'当前人气值：{popularity}')
            lastPopularity = popularity
            if lastPopularity > highestPopularity:
                highestPopularity = lastPopularity

    async def _on_receive_danmaku(self, danmaku: blivedm.DanmakuMessage):
        print(f'{danmaku.uname}：{danmaku.msg}')
        await text2Speech(danmaku.msg)
        if "串门" in danmaku.msg:
            await text2Speech("欢迎" + danmaku.uname + "来串门")
        signal = danmaku.msg[0:3]
        if signal == "#点歌":
            print("Detected song request")
            keyword = danmaku.msg[4:]
            print("Requested song: "+keyword)
            song = await searchSong(keyword)
            #print(song)
            if song:
                await addToList(song, songList)
            else:
                await text2Speech("点歌失败，没有搜索到匹配" + keyword + "的歌曲")
        elif signal[0:3] == "点歌 ":
            print("Detected song request")
            keyword = danmaku.msg[3:]
            print("Requested song: "+keyword)
            song = await searchSong(keyword)
            #print(song)
            if song:
                await addToList(song, songList)
            else:
                await text2Speech("点歌失败，没有搜索到匹配" + keyword + "的歌曲")
        elif "点歌 " in danmaku.msg:
            await text2Speech("你可能想要点歌？请注意右上角点歌格式哦")

    async def _on_receive_gift(self, gift: blivedm.GiftMessage):
        global income
        print(f'{gift.uname} 赠送{gift.gift_name}x{gift.num} （{gift.coin_type}币x{gift.total_coin}）')
        await text2Speech('感谢' + gift.uname + '赠送的' + gift.gift_name)
        if gift.coin_type == "gold":
            income += gift.total_coin

    async def _on_buy_guard(self, message: blivedm.GuardBuyMessage):
        print(f'{message.username} 购买{message.gift_name}')

    async def _on_super_chat(self, message: blivedm.SuperChatMessage):
        print(f'醒目留言 ¥{message.price} {message.uname}：{message.message}')


async def main():
    global neteasePhone
    global neteasePasswd
    global roomid
    # 参数1是直播间ID
    # 如果SSL验证失败就把ssl设为False

    #为了方便可保存在此（务必注意安全）
    #neteasePhone = ""
    #neteasePasswd = ""
    #await phoneLogin(neteasePhone, neteasePasswd)
    #roomid = 3458224
    client = MyBLiveClient(roomid, ssl=True)
    future = client.start()
    #await refreshLogin()
    try:
        # 5秒后停止，测试用
        # await asyncio.sleep(5)
        # future = client.stop()
        # 或者
        # future.cancel()

        await future
    finally:
        await client.close()


if __name__ == '__main__':
    print("Pyblive " + version  + " " + versionStatus + " build " + str(build))
    print("Thanks for using pyblive client! Developed by: Sidi Liang")
    print("Based on:")
    print("blivedm: https://github.com/xfgryujk/blivedm")
    print("Netease music API: https://github.com/Binaryify/NeteaseCloudMusicApi")
    #print("Netease Music account is required. We won't save your account and password, those information will only be sent to Netease for authentication.")
    print("Type 'help' for usage")
    #neteasePhone = input("Type your Netease cellphone account: ")
    #neteasePasswd = getpass.getpass("Type your Netease password: ")
    roomid = input("Type your Room ID here: ")
    keyboardLoop = asyncio.new_event_loop()
    mediaLoop = asyncio.new_event_loop()
    t = threading.Thread(target=listenKeyboard, name='keyboardListeningThread', args=(keyboardLoop,))
    t.start()
    t2 = threading.Thread(target=mediaControlLoop, name='mediaControlThread', args=(mediaLoop,))
    t2.start()
    asyncio.get_event_loop().run_until_complete(main())
