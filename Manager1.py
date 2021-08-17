#	
#	Copyright and disclaimer 著作権および免責事項について
#	
#	This software is made available for use by end users only.
#	このソフトウェアの入手はエンドユーザーのみによる使用を目的とするものにのみ限られます。
#	Any reproduction, copying, modification or redistribution of this software is expressly prohibited.
#	このソフトウェアの改変、複製、再頒布は固く禁止されています。
#	I assumes no responsibility or liability for any costs, damages, etc. arising from the use of this software.
#	このソフトウェアに使用によって生じたいかなる損害や費用等の一切について私は責任を負いません。
# 	
#	Hiroaki KUSANO, Aug 17 2021
#	

import os
import tkinter as tk
from tkinter import filedialog		# ファイル選択ダイアログを呼び出すために必要。何故かtkinterだけでは呼べない。
import numpy as np					# argsort を使うために必要
import subprocess					# GrassHopperを外部プログラムとして呼び出すために使う。
import re							# 正規表現
import threading			# バックグラウンドでpingを読みに行く処理に使う
import time					# pingを読みに行く間隔の間メインプロセスに処理を返すのに使う
import random

# 仮のデータ。変数名が悪い。どうにかしたい。
project = 'untitled'			# プロジェクト名の初期値
filepass = project + '.prj'		# プロジェクトファイル名の初期値。セーブしたりするとパスも付いた状態になる

filelist = ['filename5.txt', 'filename2.txt', 'filename1.txt', 'filename4.txt', 'filename3.txt']
filepasslist =['','','','','']
venderlist = ['thermo', 'waters', 'waters', 'thermo', 'sciex']
vendercode = [1, 0, 0, 1, 2]
vendersign = []
convert_sign1 = []
#convert_sign2 = []
colorlist = ['red','yellow','skyblue','blue','palegreen']
showhidelist = [1,0,0,1,0]
factorlist = [0,1,2,3,4]
factorlist_color = ['#a0f37b']*5		# 色設定用の関数で設定する
orderlist_color = ['#50f3a0']*5			# 色設定用の関数で設定する
manuallist_color = ['#3205f4']*5		# 色設定用の関数で設定する
colorswitchlist = [0,0,1,2,0]
standard_mz = [545.2345, 845.432, 611.3215, 200.000, 100.000]
standard_calib = [False, True, False, True, False]
standard_name = ['10DAB', 'paclitaxel', 'baccatin', '', '']
standard_rt = [6.1,8.3,7.0,5.2,6.5]
standard_composi = ['C31H36O11','','C47H51NO14','','']
standard_valence = [1,1,1,1,1]

# プロジェクトファイルをロードする全部上書きロード
def load_project():
	global message_frame1
	global message_frame1_label
	global project
	global filepass
	global filelist
	global filepasslist
	global venderlist
	global vendercode
	global colorlist
	global factorlist
	global manuallist_color
	global showhidelist		# int型
	global standard_mz		# float型
	global standard_calib	# bool型
	global standard_name
	global standard_rt		# float型
	global standard_composi
	global standard_valence
	global loadmode
	global ping_dat
	global ping_file
	global ping_std
	global vendersign
	global convert_sign1
#	global convert_sign2
	
	# 実行ファイルの隣のファイルを読んで前回のプロジェクトを探す
	project_pass = ''
	memoryfile = os.path.dirname(os.path.abspath(__file__)) + '/' + 'GrassHopper_settings.txt'
	if(os.path.isfile(memoryfile)):
		filehandle = open(memoryfile)
		p = filehandle.readline()	# １行目にprojectファイルのパスを書いておくことにする
		project_pass = p.split('\n')[0]
		v = filehandle.readline()	# ２行目はProteoWizard のアウトプットを処理するためのワード
		ve = v.split('\n')[0]
		vendersign = ve.split('\t')
		c1 = filehandle.readline()	# ３行目はProteoWizard のアウトプットを処理するためのワード
		co1 = c1.split('\n')[0]
		convert_sign1 = co1.split('\t')
#		c2 = filehandle.readline()	# ４行目もProteoWizard用。要らないかも
#		co2 = c2.split('\n')[0]
#		convert_sign2 = co2.split('\t')
		filehandle.close()
	
	# 何かエラーだった場合はデフォルトのファイル名を用意
	filenamepass = 'untitled.prj'
	if(os.path.isfile(project_pass)):	# 前回のプロジェクトファイルが見つかった場合
		filenamepass = project_pass
	
	# ユーザーがボタンで呼んだときはファイル選択ダイアログを出す
	if(loadmode == 'user'):
		filenamepass = filedialog.askopenfilename(filetypes = [('GrassHopper Project', 'prj'),('all files', '*')])
	loadmode = 'user'
	
	# ファイル選択がキャンセルされたり、デフォルトのファイルがない場合、不測のエラーだったりした場合
	if(not os.path.isfile(filenamepass)):
		message_frame1 = 'Load Project: missing file ' + filenamepass
		message_frame1_label.set(message_frame1)
		return
	
	# 選んだファイルがプロジェクトファイルかどうか調べる
	flag = 0
	if(os.path.isfile(filenamepass)):
		filehandle = open(filenamepass)
		line1 = filehandle.readline()
		if('GrassHopper User Settings' in line1):
			flag = 1
			filepass = filenamepass
		filehandle.close()
	
	# 中身をロードする
	if(flag == 1):
		filelist.clear()
		filepasslist.clear()
		venderlist.clear()
		vendercode.clear()
		factorlist.clear()
		manuallist_color.clear()
		showhidelist.clear()		# int型
		colorswitchlist.clear()		# int型
		standard_mz.clear()		# float型
		standard_calib.clear()	# bool型
		standard_name.clear()
		standard_rt.clear()		# float型
		standard_composi.clear()
		standard_valence.clear()
		
		vendersymbol = ['waters','thermo','sciex','shimadzu','bruker']
		filehandle = open(filenamepass)
		dammy = filehandle.readline()	# ２行飛ばす
		dammy = filehandle.readline()
		while(flag == 1):
			line = filehandle.readline()
			if(line == ''):					# 最後の行まで来ちゃった
				flag = 3
				break
			if('Expected m/z' in line):		# 標品データのとこまできた
				flag = 2
				break
			line = line.replace('\n','')	# 改行を取り除いてデータをsplitし配列に格納
			s = line.split('\t')
			filepasslist.append(s[0])
			t = s[0].split('/')
			filelist.append(t[-1])
			venderlist.append(s[1])
			for v in range(0,len(vendersymbol)):
				if(s[1] == vendersymbol[v]):
					vendercode.append(v)
					break
			if(s[2]==''):s[2]='#00FF00'
			colorlist.append(s[2])	# 仮に。
			showhidelist.append(int(s[3]))
			factorlist.append(s[4])
			colorswitchlist.append(int(s[5]))
			manuallist_color.append(s[6])
		while(flag == 2):
			line = filehandle.readline()
			if(line == ''):					# 最後の行まで来ちゃった
				flag = 3
				break
			line = line.replace('\n','')
			s = line.split('\t')
			if(s[0] == ''):s[0]=0
			if(s[2] == ''):s[2]=0
			standard_mz.append(float(s[0]))		# float型
			standard_name.append(s[1])
			standard_rt.append(float(s[2]))		# float型
			standard_calib.append(bool(int(s[3])))	# int型 -> bool型へ
			standard_composi.append(s[4])
			standard_valence.append(s[5])
		filehandle.close()
		
		# project と filepass も更新、画面に反映
		filepass = filenamepass
		temp_split = filenamepass.split('/')
		project = re.sub(r'\.prj$','',temp_split[-1])
		root.title('GrassHopper Manager: ' + project)
		message_frame1 = 'Load Project: filename= ' + temp_split[-1]
		message_frame1_label.set(message_frame1)
		
		set_color()
		refresh_frame3()
		refresh_frame6()
		print(project, filepass)
		
		ping_dat = 1
		ping_file = 1
		ping_std = 1

# ファイル名から実験に関する情報を読み出して色見本を作る。とりあえず数的な要素のみ。controlとかは後で考えよう。
def set_color():
	global factorlist
	global factorlist_color
	global orderlist_color
	global colorlist
	global ping_file
	if(len(filelist)>0):
		factorlist_color = [''] * len(factorlist)	# factorリストの色の方を初期化する
		
		# ファイル名から時間要素を探してリストする。factor欄はユーザー入力欄。空欄になるとfactorlist[f]の中身が''になる
		for f in range(0, len(filelist)):
			if(factorlist[f] == ''):		# add_filelist で設定される初期値または空欄だった場合
				factorlist[f] = read_factor(filelist[f])
		
		# 時間要素を色に変換する
		factorlist_num = [int(a) for a in factorlist]	# max min を使いたいが文字列型なので一回int型でコピーする
		mx = max(factorlist_num)
		mn = min(factorlist_num)
		for f in range(0,len(filelist)):
			if(factorlist[f] != ''):
				factorlist_color[f] = hexcolor(factorlist[f], mx, mn)
		
		# orderの欄にも色を設定する。factorとは関係ない。
		orderlist_color.clear()
		mx = len(filelist)-1
		for f in range(0,len(filelist)):
			orderlist_color.append(hexcolor(f,mx,0))
		
		# 最終的な色もここでセットする
		colorlist.clear()
		for f in range(0,len(filelist)):		# 表示色の情報はデータセットから計算することになってしまった。
			col = [orderlist_color[f], factorlist_color[f], manuallist_color[f]]
			colorlist.append( col[colorswitchlist[f]] )
		ping_file = 1
	
# ファイル名からfactor要素を探して返す関数
def read_factor(filename):
	unit = ['year', 'month', 'week', 'day', 'hour','hr', 'min', 'sec']
	num = '0'	# ユーザー入力は文字列型なので文字で。
	for uni in unit:	# 一応全部計算する。後に見つけた方で上書きするので後ろのほうが優先になる
		if(re.search(r'[0-9]+%s' % uni, filename)):
			n = re.search(r'[0-9]+%s' % uni, filename)
			nu = re.search(r'[0-9]+', n.group())
			num = nu.group()
	return(num)		# numという名前だが文字列型なので注意。

# 内部関数。引数は色に変換したい数値、範囲大、範囲小を与える。数字か数値でOK
def hexcolor(v, mx, mn):
	if(mx <= mn):return('#00FF00')
	val = (int(v)-int(mn))/(int(mx)-int(mn))
	r = int(511*val)
	g = int(511*(1.0-val))
	b = 0
	if(r>255):r=255
	if(g>255):g=255
	hx = hex(256*256*r + 256*g + b)
	hx = re.sub('0x', '', hx)
	if(r<16):hx = '0' + hx
	if(r==0):hx = '0' + hx
	return('#'+hx)				# 色を #FFAA00 のフォーマットで返す

# プロジェクトファイルのセーブ先をユーザーの入力から得る
def input_savefilepass():
	global message_frame1
	global message_frame1_label
	global project
	global filepass
	global ping_dat
	
	# 保存先ファイル名をユーザーに尋ねる
	initialfilename = project + '.prj'		# 初期ファイルを設定すると勝手にファイル生成＆上書きがされなくなった。
	filenamepass = filedialog.asksaveasfilename(initialfile = initialfilename, 
						filetypes = [('GrassHopper Project', 'prj'),('all files', '*')])
	# 大丈夫かどうか調べる
	if(filenamepass):	# キャンセルが押されていた場合はelseに行く。
		s = filenamepass.split('/')		# ファイル名部分を取り出す。splitした最後がファイル名。
		filename = s[-1]
		
		# filadialogが末尾に拡張子を付加してくれなかったときの対応
		if(not bool(re.search(r'\.prj$', filename))):
			filename += '.prj'		# ファイル名末尾に拡張子が無かったら拡張子を追加する
			filenamepass += '.prj'
		
		# プロジェクト名を書き換える。ファイル名から拡張子を取り外したもの
		project = re.sub(r'\.prj$', '', filename)
		
		# ユーザーがミスってファイル名を消してsaveボタンを押した場合の対応。ファイル名が .prj.prj になっている。
		if(re.search('^\.', project)):	# うっかり初期表示のファイル名を消してsaveボタンを押した場合は拡張子だけになっているので対応が必要
			project = 'noname'			# ついでにファイル名の方も対応しておく。ファイル名が.で始まると面倒なのでnonameとかいう名前にする
			filename = 'noname.prj'
			filenamepass = 'noname.prj'
		root.title('GrassHopper Manager: ' + project)
		
		message_frame1 = 'Save Project: filename= ' + filename
		message_frame1_label.set(message_frame1)
		
		# 現在の状況をセーブしよう。関数を作って呼ぶことになりそうだからそうしよう
		filepass = filenamepass
		ping_dat = 1
		save_project()
		
	else:
		message_frame1 = 'Save Project: cancelled'
		message_frame1_label.set(message_frame1)
		filename = initialfilename		# キャンセルされると空っぽになる。パス付きの方はどうしようもない。

# プロジェクトファイルをセーブする。データファイルもセーブする。分けたほうがいいかな。
def save_project():
	global filepass
	global ping_dat
	
	# プロジェクトファイルをセーブ。ファイル名が壊れてることはないけどパスが無い場合はある。
	if(not bool(re.search(r'\/', filepass))):		# filepassに / があったらいいが、ない場合はカレントディレクトリを使用
		message_frame1 = 'Save Project: currentdir/' + filepass
		message_frame1_label.set(message_frame1)
		filepass = os.getcwd() + '/' + filepass
	else:
		s = re.sub(project+'.prj','',filepass)
		front = re.search('^.{10}',s).group()
		rear = re.search('.{10}$',s).group()
		message_frame1 = 'Save Project: ' + front + '...' + rear + project + '.prj'
		message_frame1_label.set(message_frame1)
	savemode = 'x'						# 上書きか新規作成か
	if(os.path.isfile(filepass)):savemode='w'
	filehandle = open(filepass, savemode)
	filehandle.write('GrassHopper User Settings\n')
	line1 = 'Filename\tVender\tColor\tshow in static mode = 1\t([tab]deliminated format)\n'
	filehandle.write(line1)
	for f in range(0,len(filelist)):
#		s = filelist[f].split('/')		# パスは要らない
#		filehandle.write(s[-1] + '\t')
		filehandle.write(filepasslist[f] + '\t')	# パスのある方を保存
		filehandle.write(venderlist[f] + '\t')
		filehandle.write(colorlist[f] + '\t')
		filehandle.write(str(showhidelist[f]) + '\t')
		filehandle.write(str(factorlist[f]) + '\t')
		filehandle.write(str(colorswitchlist[f]) + '\t')
		filehandle.write(manuallist_color[f] + '\n')
		
	line2 = 'Expected m/z\tlabel\tretention time\tuse as calibration standard = 1\t([tab]deliminated format)\n'
	filehandle.write(line2)
	for s in range(0,len(standard_mz)):
		if(float(standard_mz[s])>0):
			filehandle.write(str(standard_mz[s])+'\t')
			filehandle.write(str(standard_name[s])+'\t')
			filehandle.write(str(standard_rt[s])+'\t')
			filehandle.write(str(int(standard_calib[s]))+'\t')		# bool型
			filehandle.write(str(standard_composi[s])+'\t')
			filehandle.write(str(standard_valence[s])+'\n')
	filehandle.close()
	
	# データもセーブする
	if(ping_dat == 1):	# ここバグを生みやすい
#		convert_data()
		save_thread = threading.Thread(target = convert_data)
		save_thread.start()
	else:
		send_ping()	# データは変わらないのであればGrassHopperに知らせる
	
	# 今回の思い出を残しておく。
	memoryfile = os.path.dirname(os.path.abspath(__file__)) + '/' + 'GrassHopper_settings.txt'
	savemode = 'x'
	if(os.path.isfile(memoryfile)):
		savemode = 'w'
	filehandle = open(memoryfile, savemode)
	filehandle.write(filepass)
	filehandle.write('\n')
	for i in range(0, len(vendersign)):
		filehandle.write(vendersign[i])
		if(i<len(vendersign)-1):
			filehandle.write('\t')
	filehandle.write('\n')
	for i in range(0, len(convert_sign1)):
		filehandle.write(convert_sign1[i])
		if(i<len(convert_sign1)-1):
			filehandle.write('\t')
	filehandle.write('\n')
#	for i in range(0, len(convert_sign2)):
#		filehandle.write(convert_sign2[i])
#		if(i<len(convert_sign2)-1):
#			filehandle.write('\t')
	filehandle.close()
#	project_pass = filehandle.readline()	# １行目にprojectファイルのパスを書いておくことにする


# データを変換する
def convert_data():
	global message_frame1
	global message_frame1_label
	global button_call
	
	button_call.configure(fg = 'gray', text = 'preparing data')
	
	data_rt=[]	# data_rt[file][sign] rt はit数分だけデータを複製する
	data_mz=[]	
	data_it=[]	
	flag_fn=[]	# フラグ
	copy_rt=[]	
	copy_mz=[]	
	copy_it=[]	
	# 既にあるファイルのデータがないかチェックする
	outfile = filepass[0:-4] + '.dat'
	if(os.path.isfile(outfile)):
		filehandle = open(outfile)
		whole_data = filehandle.read()	# まるごとロード
		filehandle.close()
		
		sp = whole_data.split('\n')
		present_files = int(len(sp)/4)
		fn = []
		for p in range(0, present_files):
			spp = sp[p*4+0].split(',')
			fn.append(spp[0])
		for f in range(0, len(filelist)):
			flag_fn.append(0)
			for p in range(0, present_files):
				if(filelist[f] == fn[p]):
					copy_rt.append(sp[p*4+1])
					copy_mz.append(sp[p*4+2])
					copy_it.append(sp[p*4+3])
					flag_fn[f] = 1
					break
			if(flag_fn[f] == 0):
					copy_rt.append('')
					copy_mz.append('')
					copy_it.append('')
	else:	# データファイルが無い場合は全部新規。
		for f in range(0, len(filelist)):
			flag_fn.append(0)
			copy_rt.append('')
			copy_mz.append('')
			copy_it.append('')
	
	for f in range(0, len(flag_fn)):
		print('convert', flag_fn[f], filelist[f], len(copy_rt[f]), flush = True)
	
	# データを抽出する。真四角のデータにする
	key1 = ['function=1', 'MS1 spectrum','MS1 spectrum','MS1 spectrum']		# MS scan のデータを示す記号。メーカーにより異なる。
	key1 = convert_sign1
	key2 = 'cvParam: scan start time'			# Rt が出てくる行。いまのところメーカーによらず共通
	for f in range(0,len(filepasslist)):
		data_rt.append([])	# data_rt[f] を使用可能にする
		data_mz.append([])
		data_it.append([])
		if(flag_fn[f]==0):
			filehandle = open(filepasslist[f])
			print(filelist[f], end = '', flush=True)
			
			signs=0	# デバッグ用だったけど、offsetを決めるのに便利なので取っておく
			scans=0
			process_monitor = 0
			
			rt_temp = 0.0
			array_rt_temp = []	# スキャン１回分のデータを処理するための一時的リスト。毎周回リセットされる。
			array_mz_temp = []
			array_it_temp = []
			data_rt_f = []		# ファイル毎のデータを処理するための一時的リスト
			data_mz_f = []
			data_it_f = []
			flag = 0
			while(flag>(-1)):
				line = filehandle.readline()		# １行ずつよんで判定する
				line = line.replace(' \n', '')
				
				if(line == ''):		# 最後の行まできた場合はおわり
					flag = (-1)
					break
				
				if(flag==0):		# MS scan のデータのある場所を探す。
					if(key1[vendercode[f]] in line):
						flag = 1
						continue
				
				if(flag==1):		# Rt の値を探す
					if(key2 in line):
						t=line.split(', ')
						rt_temp = float(t[1])	# splitしたふたつめがRtのデータ。str型だがどこで変換しようか。
						flag = 2
						continue
				
				if(flag==2):		# m/z のリストを探す
					if('binary:' in line):
						s = line.split('] ')
						array_mz_temp.clear()
						array_mz_temp = s[1].split(' ')
						array_mz_temp = [float(n) for n in array_mz_temp]
						flag = 3
						continue
						
				if(flag==3):		# it のリストを探す
					if('binary:' in line):
						s = line.split('] ')
						array_it_temp.clear()
						array_it_temp = s[1].split(' ')
						array_it_temp = [float(n) for n in array_it_temp]
						
						# これで１スキャン分のデータが揃った。rt,mz,itをそれぞれファイル単位のリストに連結する
						if(len(array_it_temp)>0):	# 有効なintensityを持つときだけ。
							array_rt_temp.clear		# ソートしたらscanはバラバラになっちゃうのでRt値はシグナル数分だけ複製する。
							array_rt_temp = [rt_temp]*len(array_it_temp)
							
							data_rt_f += array_rt_temp	# 一時リストに連結する
							data_mz_f += array_mz_temp	# ここを a = a + b と書くと激遅
							data_it_f += array_it_temp	# ここは a += b と書くべし。
							
							signs += len(array_it_temp)			# 重いと止まって見えるので何かconsoleに表示させる
							scans += 1
							if(process_monitor < int(scans/500)):
								process_monitor = int(scans/500)
								print('.', end = '', flush = True)
							
						flag=0
						continue
			message_frame1 = 'Save Project: converting ' + filelist[f]
			message_frame1_label.set(message_frame1)
			
			# argsort を使いたいのでファイルごとのリスト３つをnumpy ndarrayに変換
			print('sorting...', end = '', flush = True)
			data_rt_np = np.array(data_rt_f, dtype = np.float32)
			print('.', end = '', flush = True)
			data_mz_np = np.array(data_mz_f, dtype = np.float32)
			print('.', end = '', flush = True)
			data_it_np = np.array(data_it_f, dtype = np.float32)
			print('.', end = '', flush = True)
			
			# Numpyの呪文でitの降順ソートを基準にデータを並べ替える
			data_it_sorted = np.sort(data_it_np)[::-1]	# itの配列を降順にソートする
			print('.', end = '', flush = True)
			sort_index = np.argsort(data_it_np)[::-1]	# itを降順ソートした順番を示すリストを得る
			print('.', end = '', flush = True)
			data_mz_sorted = data_mz_np[sort_index]		# Rt と mz も同じindex順で並べ替える
			print('.', end = '', flush = True)
			data_rt_sorted = data_rt_np[sort_index]
			print('.', end = '', flush = True)
			
			# メインデータに追加する。ndarrayは真四角じゃないとダメなのでリストを使う。appendでなく+=で。
			signalnum_limit = data_it_sorted.size	# データ量が多すぎるときはカットする。１データあたり100万シグナルくらいだといい
			if(signalnum_limit > 1000000):
				print('over limit', signalnum_limit, end='', flush=True)
				signalnum_limit = 1000000
			data_rt[f] += data_rt_sorted[:signalnum_limit].tolist()
			print('.', end = '', flush = True)
			data_mz[f] += data_mz_sorted[:signalnum_limit].tolist()
			print('.', end = '', flush = True)
			data_it[f] += data_it_sorted[:signalnum_limit].tolist()
			print(signalnum_limit, ' signals')
			
			filehandle.close()
	
	# セーブする。ぜんぶ変換済みであっても順番が変わったりしているので保存はしておこう。
	message_frame1 = 'Save Project: creating ' + project + '.dat'
	message_frame1_label.set(message_frame1)
	print('writing into file...', end='', flush = True)
	savemode = 'x'
	if os.path.isfile(outfile):savemode = 'w'
	savehandle = open(outfile, savemode)
	for f in range(0, len(filepasslist)):
		data_r = copy_rt[f]
		data_m = copy_mz[f]
		data_i = copy_it[f]
		if(flag_fn[f] == 0):
			data_r = ','.join(map(str,data_rt[f]))		# Numpyでastype('str') とか astype('unicode')はNG。何故かケタが減る。
			data_m = ','.join(map(str,data_mz[f]))
			data_i = ','.join(map(str,data_it[f]))
		savehandle.write(filelist[f])
		savehandle.write(',')
		savehandle.write(str(vendercode[f]))
		savehandle.write('\n')
		savehandle.write(data_r)
		savehandle.write('\n')
		savehandle.write(data_m)
		savehandle.write('\n')
		savehandle.write(data_i)
		savehandle.write('\n')
		print('.', end = '', flush = True)
	savehandle.close()
	print('done')
	message_frame1 = 'Save Project: ' + project + '.dat done'
	message_frame1_label.set(message_frame1)
	send_ping()
	button_call.configure(fg = 'blue', text = 'Call GrassHopper')

# ライブラリをロードする。まだロードしない。
def load_library():
	print('Manager: load_library_called')	# とりあえず呼ばれたことがわかるように。

# GrassHopperを呼び出す。３つめの引数でGrassHopperにProjectパスを渡したい。
def call_grasshopper():
	save_project()
	subprocess.Popen([r'python', r'GrassHopper1.py', filepass])	# プロジェクト名とパスを引数に渡す必要がありそう


# GrassHopperとの連携に使う変数
ping_dat = 0
ping_file = 0
ping_std = 0
ping_export = 0		# 受け取る方は1になることがないかな。

# GrassHopperに変更があったことを伝える。ファイル経由で。あっちから定期的に読みに来ることにしよう。
def send_ping():
	global ping_dat
	global ping_file
	global ping_std
	pingpass = os.getcwd() + '/' + project +'.ping'	# 複数のGrassHopperを動かすことを想定する。プロジェクト名を鍵にして管理する
	pingpass = filepass[0:-4] + '.ping'
	
	savemode = 'x'					# とりあえずのgetcwd()はカレントディレクトリ。インストールディレクトリ的なものを使いたい。
	if(os.path.isfile(pingpass)):
		savemode='w'
	filehandle = open(pingpass, savemode)
	filehandle.write('to GrassHopper\n')
	filehandle.write(str(ping_dat) + '\tdatfile changed\n')	# スイッチ用の変数を用意しよう。
	filehandle.write(str(ping_file) +'\tfilelist changed\n')
	filehandle.write(str(ping_std) + '\tstandard changed\n')
	filehandle.write('to Manager\n')
	filehandle.write(str(ping_export) +'\tdata exported\n')		# ６行目は受け取る行
	filehandle.close()
	
	print('send_ping: ', ping_dat, ping_file, ping_std)
	ping_dat = 0
	ping_file = 0
	ping_std = 0

# pingを見に行く。
def load_ping():
	global ping_export
	while(1):
		pingpass = os.getcwd() + '/' + project +'.ping'	# 複数のGrassHopperを動かすことを想定する。プロジェクト名を鍵にして管理する
		pingpass = filepass[0:-4] + '.ping'
		if(os.path.isfile(pingpass)):
			filehandle = open(pingpass)
			dm1 = filehandle.readline()
			dm2 = filehandle.readline()
			dm3 = filehandle.readline()
			dm4 = filehandle.readline()
			dm5 = filehandle.readline()
			line = filehandle.readline()
			filehandle.close()
			
			s = line.split('\t')
			if(s[0] == '1'):
				load_library()
				ping_export = 0
				send_ping()		# pingをリセット
			# print('load_ping')
		time.sleep(3)


# フレーム３のファイルリストをソートする。
sort_switch_file = 1
sort_switch_column = 0
def sort_filelist():
	global sort_switch_file
	global filelist
	global filepasslist
	global venderlist
	global showhidelist
	global colorlist
	global factorlist
	global factorlist_color
	global manuallist_color
	global colorswitchlist
	global sort_switch_column
	global ping_dat
	
	filelist_np = np.array(filelist)			# argsortを使うのでnumpy化
	filepasslist_np = np.array(filepasslist)
	venderlist_np = np.array(venderlist)
	showhidelist_np = np.array(showhidelist)
	colorlist_np = np.array(colorlist)
	factorlist_np = np.array(factorlist)
	factorlist_color_np = np.array(factorlist_color)
	manuallist_color_np = np.array(manuallist_color)
	colorswitchlist_np = np.array(colorswitchlist)
	
	filesort_index = np.argsort(filelist_np)[::sort_switch_file]	# ソートの基準にする列を選ぶ
	if(sort_switch_column == 1):	# スイッチが1に入ってる場合はfactorボタンで呼ばれた
		factorlist_int = np.array(factorlist, dtype=np.int32)
		filesort_index = np.argsort(factorlist_int)[::sort_switch_file]
	
	filelist_np_sorted =  filelist_np[filesort_index]			# ソートする
	filepasslist_np_sorted =  filepasslist_np[filesort_index]
	venderlist_np_sorted = venderlist_np[filesort_index]
	showhidelist_np_sorted = showhidelist_np[filesort_index]
	colorlist_np_sorted = colorlist_np[filesort_index]
	factorlist_np_sorted = factorlist_np[filesort_index]
	factorlist_color_np_sorted = factorlist_color_np[filesort_index]
	manuallist_color_np_sorted = manuallist_color_np[filesort_index]
	colorswitchlist_np_sorted = colorswitchlist_np[filesort_index]
	
	filelist = filelist_np_sorted.tolist()				# リストに戻す
	filepasslist = filepasslist_np_sorted.tolist()
	venderlist = venderlist_np_sorted.tolist()
	showhidelist = showhidelist_np_sorted.tolist()
	colorlist = colorlist_np_sorted.tolist()
	factorlist = factorlist_np_sorted.tolist()
	factorlist_color = factorlist_color_np_sorted.tolist()
	manuallist_color = manuallist_color_np_sorted.tolist()
	colorswitchlist = colorswitchlist_np_sorted.tolist()
	
	sort_switch_file = sort_switch_file * (-1)		# スイッチを切り替える
	sort_switch_column = 0		# デフォルト値はファイル名ソート。ファイル名ソートのボタンはスイッチ切り替え関数を通らず直結でここに来る
	
	set_color()		# 色を整えて全面的に表示を治す
	refresh_frame3()
	ping_dat = 1
def sort_by_factor():
	global sort_switch_column
	sort_switch_column = 1		# ソートのスイッチをfactorの列に切り替えてソート関数を呼ぶ
	sort_filelist()

# フレーム３のリストに新しいファイルを追加する。ユーザー選択からベンダーまで判定する
def add_filelist():
	global filelist
	global filepasslist
	global venderlist
	global showhidelist
	global colorswitchlist
	global colorlist
	global manuallist_color
	global factorlist
	global ping_dat
	
	vendersymbol = ['waters','thermo','sciex','shimadzu','bruker']
	newfilename = filedialog.askopenfilenames()		# リストで返る
	if(len(newfilename)>0):
		for filepassname in newfilename:
			ff = filepassname.split('/')
			filename = ff[-1]
			flag = 0
			for f in filelist:		# 同じ名前のファイルが既にないかチェック
				if(filename == f):
					flag = 1
					break
			if(flag == 1):continue
			filehandle = open(filepassname)		# 新しいファイルの場合は中身をチェック
			line = filehandle.readline()
			if('msdata:' in line):	# 一行めに'msdata'とあったら第一段階突破
				flag = (-1)
				c = 0
				while(c<1000):		# vender情報を探す
					search = filehandle.readline()
					for i in range(0, len(vendersign)):
						if(vendersign[i] in search):
							flag = i
							print(filename, vendersymbol[i])
							break
#					if('MassLynx' in search):
#						flag = 0
#						print(filename, 'waters')
#						break
#					if('Thermo' in search):
#						flag = 1
#						print(filename, 'thermo')
#						break
#					if('Analyst' in search):
#						flag = 2
#						print(filename, 'sciex')
#						break
#					if('yyyyy' in search):
#						flag = 3
#						print(filename, 'shimadzu')
#						break
#					if('zzzzz' in search):
#						flag = 4
#						print(filename, 'bruker')
#						break
					c += 1
				if(flag > (-1)):	# venderまで見つかったらOKとする
					filelist.append(filename)
					filepasslist.append(filepassname)
					vendercode.append(flag)
					venderlist.append(vendersymbol[flag])
					showhidelist.append(1)
					colorlist.append('#00FF00')
					defaultcolor = hex(random.randint(0, 0xFFFFFF))[2:]
					defaultcolor = ('#' + '0' * (6-len(defaultcolor)) + defaultcolor).upper()
					manuallist_color.append(defaultcolor)
					factorlist.append('')			# factor の初期値。
					colorswitchlist.append(0)		# 色スイッチ の初期値。
			filehandle.close()
		set_color()	# factor に値を入れる
		refresh_frame3()
		ping_dat = 1

# フレーム３のラジオボタンshow/hide への入力に反応する関数。画面の状況をデータに反映させる
def set_showhidelist():
	global showhidelist
	global ping_file
	for f in range(0,len(showhidelist)):
		showhidelist[f] = radiobutton_fileshow_var[f].get()
	ping_file = 1

# フレーム３のラジオボタン色スイッチへの入力に反応する関数。画面の状況をデータに反映させる
def set_colorswitchlist():
	global colorswitchlist
	global ping_file
	for f in range(0,len(colorswitchlist)):
		colorswitchlist[f] = radiobutton_colorswitch_var[f].get()
		col = [orderlist_color[f], factorlist_color[f], manuallist_color[f]]
		color = col[colorswitchlist[f]]
		colorlist[f] = color
		label_files[f].configure(bg=color)
	ping_file = 1

# フレーム３のdeleteボタンの反応。ボタンのコールバックcommandから引数つきで呼ぶためにクロージャ関数を使う。
def pop_file(num):
	global filelist
	global filepasslist
	global venderlist
	global showhidelist
	global colorswitchlist
	global colorlist
	global manuallist_color
	global factorlist
	global factorlist_color
	global ping_dat
	filelist.pop(num)
	filepasslist.pop(num)
	venderlist.pop(num)
	showhidelist.pop(num)
	colorswitchlist.pop(num)
	colorlist.pop(num)
	manuallist_color.pop(num)
	factorlist.pop(num)
	factorlist_color.pop(num)
	set_color()
	refresh_frame3()
	ping_dat = 1
def make_popfile(f):
	def pop_file_():
		pop_file(f)
	return pop_file_	# 生成される関数のことをクロージャー関数というらしい。

# フレーム３を書き直す。
def refresh_frame3():
	global subframe3
	global label_order3
	global label_files
	global button_del
	global radiobutton_fileshow_var
	global radiobutton_showswitch1
	global radiobutton_showswitch2
	global radiobutton_colorswitch_var
	global radiobutton_colorswitch1
	global radiobutton_colorswitch2
	global radiobutton_colorswitch3
	global label_vender
	global factorlist_var
	global entry_factor
	global manualcolor_var
	global entry_color
	global button_addnewfile
	global ping_file
	
	
	for f in range(0, len(label_order3)):		# まずpack_forget でウィジェットを一旦表示オフ
		label_order3[f].pack_forget()
		label_files[f].pack_forget()
		button_del[f].pack_forget()
		radiobutton_showswitch1[f].pack_forget()
		radiobutton_showswitch2[f].pack_forget()
		radiobutton_colorswitch1[f].pack_forget()
		radiobutton_colorswitch2[f].pack_forget()
		radiobutton_colorswitch3[f].pack_forget()
		label_vender[f].pack_forget()
		entry_color[f].pack_forget()
		subframe3[f].pack_forget()
	button_addnewfile.pack_forget()
	
	label_order3.clear()				# ウィジットのオブジェクトの配列も一旦clear
	label_files.clear()
	button_del.clear()
	radiobutton_fileshow_var.clear()
	radiobutton_showswitch1.clear()
	radiobutton_showswitch2.clear()
	radiobutton_colorswitch_var.clear()
	radiobutton_colorswitch1.clear()
	radiobutton_colorswitch2.clear()
	radiobutton_colorswitch3.clear()
	label_vender.clear()
	entry_color.clear()
	factorlist_var.clear()
	manualcolor_var.clear()
	entry_factor.clear()
	subframe3.clear()
	
	for f in range(0, len(filelist)):
		radiobutton_fileshow_var.append(tk.IntVar())
		radiobutton_fileshow_var[f].set(showhidelist[f])
		factorlist_var.append(tk.StringVar())		# コールバック変数？を宣言して値を入れる
		factorlist_var[f].set(factorlist[f])
		manualcolor_var.append(tk.StringVar())		# コールバック変数？を宣言して値を入れる
		manualcolor_var[f].set(manuallist_color[f])
		radiobutton_colorswitch_var.append(tk.IntVar())
		radiobutton_colorswitch_var[f].set(colorswitchlist[f])
		
		subframe3.append(tk.Frame(frame3))
		label_order3.append(tk.Label(subframe3[f], text = str(f+1), width = 4, anchor = tk.CENTER, bg=orderlist_color[f]))
		label_files.append(tk.Label(subframe3[f], text = filelist[f], width = 24, anchor = tk.E, bg=colorlist[f]))
		button_del.append(tk.Button(subframe3[f], text = 'delete', command = make_popfile(f), width = 3))
		radiobutton_showswitch1.append(tk.Radiobutton(subframe3[f], value='1', 
					variable = radiobutton_fileshow_var[f], command = set_showhidelist))
		radiobutton_showswitch2.append(tk.Radiobutton(subframe3[f], value='0', 
					variable = radiobutton_fileshow_var[f], command = set_showhidelist))
		label_vender.append(tk.Label(subframe3[f], text = venderlist[f], width = 6))
		entry_factor.append(tk.Entry(subframe3[f], width = 6, justify = tk.CENTER, 
					textvariable = factorlist_var[f], bg=factorlist_color[f]))
		radiobutton_colorswitch1.append(tk.Radiobutton(subframe3[f], value='0', bg=orderlist_color[f], 
					variable = radiobutton_colorswitch_var[f], command = set_colorswitchlist))
		radiobutton_colorswitch2.append(tk.Radiobutton(subframe3[f], value='1', bg=factorlist_color[f], 
					variable = radiobutton_colorswitch_var[f], command = set_colorswitchlist))
		radiobutton_colorswitch3.append(tk.Radiobutton(subframe3[f], value='2', bg=manuallist_color[f], 
					variable = radiobutton_colorswitch_var[f], command = set_colorswitchlist))
		entry_color.append(tk.Entry(subframe3[f], width = 8, justify = tk.CENTER, 
					textvariable = manualcolor_var[f], bg=manuallist_color[f], ))
		
		label_order3[f].pack(side = tk.LEFT)
		label_vender[f].pack(side = tk.LEFT)
		label_files[f].pack(side = tk.LEFT)
		button_del[f].pack(side = tk.LEFT)
		radiobutton_showswitch1[f].pack(side = tk.LEFT)
		radiobutton_showswitch2[f].pack(side = tk.LEFT)
		entry_factor[f].pack(side = tk.LEFT)
		entry_color[f].pack(side = tk.LEFT)
		radiobutton_colorswitch1[f].pack(side = tk.LEFT)
		radiobutton_colorswitch2[f].pack(side = tk.LEFT)
		radiobutton_colorswitch3[f].pack(side = tk.LEFT)
		subframe3[f].pack(side = tk.TOP)
	
		entry_factor[f].bind("<KeyRelease>", func = activate_entry_factor)		# factor欄のEntry窓への入力に反応するイベントを設定
		entry_color[f].bind("<Return>", func = activate_entry_color)		# manual欄のEntry窓への入力に反応するイベントを設定

	button_addnewfile.pack(side = tk.TOP, anchor = tk.W)
	ping_file = 1

# フレーム３のfactor欄へのユーザー入力に反応する関数。何故か引数を一個受け取ることにしないとエラーになる。
def activate_entry_factor(dammy):
	global factorlist
	for f in range(0, len(filelist)):
		factorlist[f] = integering(factorlist_var[f].get(), filelist[f])
	set_color()
	for f in range(0, len(filelist)):
		factorlist_var[f].set(factorlist[f])
		entry_factor[f].configure(bg=factorlist_color[f])
def integering(strings, filename):
	strings = re.sub(r'[^0-9]', '', strings)	# 数字か小数点以外の文字が入っていたら取り除く
	integer = 0
	if(strings == ''):
		integer = 1
		if(filename==''):return(integer)	# この関数を価数を入力する欄のために使っちゃった。そっちは第２引数を''で呼び出して、空欄のときは1がいい
		integer = int(read_factor(filename))	# ここにfactorを読み出す処理を書く。
	else:
		integer = int(strings)
	return(integer)

# フレーム３のmanual欄へのユーザー入力に反応する関数。何故か引数を一個受け取ることにしないとエラーになる。
def activate_entry_color(dammy):
	global manuallist_color
	global ping_file
	preset_color = [	['red',		'#FF0000'],		# openGL で半端な色が何故か出ないからFFが必ず入る
						['green',	'#00FF00'],
						['blue',	'#0000FF'],
						['yellow',	'#FFFF00'],
						['orange',	'#FF7700'],
						['skyblue',	'#00FFFF'],
						['purple',	'#7700FF'],
						['pink',	'#FF00FF'],
						['white',	'#FFFFFF']	]
	for f in range(0, len(filelist)):
		strings = manualcolor_var[f].get()
		if(strings != manuallist_color[f]):		# 書き換えが発生していた行
			color = ''
			if(re.search(r'[0-9A-Fa-f]{6}',strings) ):		# 指定がRRGGBBだったとき
				color = '#' + re.search(r'[0-9A-Fa-f]{6}',strings).group().upper()
			if(re.match(r'[A-Za-z]+', strings) ):			# 指定が文字だったとき
				for i in range(0, len(preset_color)):
					if(strings.lower() == preset_color[i][0]):
						color = preset_color[i][1]
						break
			if(strings == ''):								# 指定が全消しだったとき
				color = hex(random.randint(0, 0xFFFFFF))[2:]
				color = ('#' + '0' * (6-len(defaultcolor)) + defaultcolor).upper()
			
			if(color == ''):	# 誤りがある場合は前のデータに戻す
				manualcolor_var[f].set(manuallist_color[f])	
			else:				# どれかにヒットした場合はそれをセット
				manuallist_color[f] = color
				colorlist[f] = color
				ping_file = 1
				colorswitchlist[f] = 2
	refresh_frame3()


# フレーム６の標品リストをソートする。
sort_switch_mz = 1
def sort_stdlist():
	global sort_switch_mz
	global standard_mz
	global standard_calib
	global standard_name
	global standard_rt
	global standard_composi
	global standard_valence
	
	stdmz_np = np.array(standard_mz)				# numpy化
	std_calib_np = np.array(standard_calib)
	std_name_np = np.array(standard_name)
	std_rt_np = np.array(standard_rt)
	std_comp_np = np.array(standard_composi)
	std_vale_np = np.array(standard_valence)

	stdsort_index = np.argsort(stdmz_np)[::sort_switch_mz]		# 基準にする列のソート順をindexにする
	stdmz_np_sorted = stdmz_np[stdsort_index]
	std_calib_sorted = std_calib_np[stdsort_index]
	std_name_sorted = std_name_np[stdsort_index]
	std_rt_sorted = std_rt_np[stdsort_index]
	std_comp_sorted = std_comp_np[stdsort_index]
	std_vale_sorted = std_vale_np[stdsort_index]
	
	standard_mz = stdmz_np_sorted.tolist()			# リストに戻す
	standard_calib = std_calib_sorted.tolist()
	standard_name = std_name_sorted.tolist()
	standard_rt = std_rt_sorted.tolist()
	standard_composi = std_comp_sorted.tolist()
	standard_valence = std_vale_sorted.tolist()
	
	sort_switch_mz = sort_switch_mz * (-1)		# 次回のソート順を逆にする。昇順／降順
	refresh_frame6()		# 表示する

# フレーム６の標品リストに空っぽの行を追加する
def add_new_std():
	global standard_mz
	global standard_calib
	global standard_name
	global standard_rt
	global standard_composi
	standard_mz.append(300.0)
	standard_calib.append(True)
	standard_name.append('')
	standard_rt.append(6.5)
	standard_composi.append('')
	standard_valence.append('1')
	refresh_frame6()
	
# フレーム６のdeleteボタンの反応。クロージャー関数というものを使う
def pop_std(num):
	global standard_mz
	global standard_calib
	global standard_name
	global standard_rt
	global standard_composi
	standard_mz.pop(num)
	standard_calib.pop(num)
	standard_name.pop(num)
	standard_rt.pop(num)
	standard_composi.pop(num)
	standard_valence.pop(num)
	refresh_frame6()
def make_popstd(s):
	def pop_std_():
		pop_std(s)		# 関数の中で関数を定義することで変数の中身を記憶した関数が生成するらしい
	return pop_std_

# フレーム６を書き直す。
def refresh_frame6():
	global subframe6
	global label_order6
	global standard_mz_var
	global standard_name_var
	global standard_rt_var
	global standard_check_var		# チェックボックスなのでbooleanVar
	global standard_composi_var
	global standard_valence_var
	global entry_mz6
	global entry_name6
	global entry_rt6
	global button_del_std
	global checkbutton_calib6
	global entry_composi6
	global entry_valence6
	global button_calc6
	global button_addnewstd
	global label_std_message
	global ping_std
	
	for s in range(0, len(label_order6)):	# まず表示をオフ
		label_order6[s].pack_forget()
		entry_mz6[s].pack_forget()
		checkbutton_calib6[s].pack_forget()
		entry_name6[s].pack_forget()
		entry_rt6[s].pack_forget()
		entry_composi6[s].pack_forget()
		entry_valence6[s].pack_forget()
		button_calc6[s].pack_forget()
		subframe6[s].pack_forget()	# subframeの表示オフは気分で最後にしてみた
		
	label_order6.clear()	# ウィジットオブジェクトの配列を一旦全部クリアする
	entry_mz6.clear()
	checkbutton_calib6.clear()
	entry_name6.clear()
	entry_rt6.clear()
	button_del_std.clear()
	entry_composi6.clear()
	entry_valence6.clear()
	button_calc6.clear()
	standard_mz_var.clear()
	standard_check_var.clear()
	standard_name_var.clear()
	standard_rt_var.clear()
	standard_composi_var.clear()
	standard_valence_var.clear()
	subframe6.clear()
	button_addnewstd.pack_forget()		# リストに下に置いているボタンはクリアしない。一旦表示だけオフ
	label_std_message.pack_forget()
	
	for s in range(0, len(standard_mz)):		# 新しいデータに従ってウィジットを生成する
		subframe6.append(tk.Frame(frame6))
		label_order6.append(tk.Label(subframe6[s], text = str(s+1), width = 2, anchor = tk.CENTER))
		
		standard_mz_var.append(tk.StringVar())		# コールバック変数？を宣言して値を入れる
		standard_check_var.append(tk.BooleanVar())
		standard_name_var.append(tk.StringVar())
		standard_rt_var.append(tk.StringVar())
		standard_composi_var.append(tk.StringVar())
		standard_valence_var.append(tk.StringVar())
		standard_mz_var[s].set(standard_mz[s])
		standard_check_var[s].set(standard_calib[s])
		standard_name_var[s].set(standard_name[s])
		standard_rt_var[s].set(standard_rt[s])
		standard_composi_var[s].set(standard_composi[s])
		standard_valence_var[s].set(standard_valence[s])
																# ウィジットを生成
		entry_mz6.append(tk.Entry(subframe6[s], textvariable = standard_mz_var[s], width = 10))
		checkbutton_calib6.append(tk.Checkbutton(subframe6[s], variable=standard_check_var[s], 
				command = activate_checkbutton_std ))	# チェックボタンはbindの代わりにコールバックを使う
		entry_name6.append(tk.Entry(subframe6[s], textvariable = standard_name_var[s], width = 14))
		entry_rt6.append(tk.Entry(subframe6[s], textvariable = standard_rt_var[s], width = 4))
		button_del_std.append(tk.Button(subframe6[s], text = 'delete', command = make_popstd(s), width = 3))
		entry_composi6.append(tk.Entry(subframe6[s], textvariable = standard_composi_var[s], width = 20))
		entry_valence6.append(tk.Entry(subframe6[s], textvariable = standard_valence_var[s], width = 2))
		button_calc6.append(tk.Button(subframe6[s], text = 'calculate m/z', command= make_calculate(s) ))
		
		label_order6[s].pack(side = tk.LEFT)		# ウィジットを配置する
		entry_mz6[s].pack(side = tk.LEFT)
		checkbutton_calib6[s].pack(side = tk.LEFT)
		entry_name6[s].pack(side = tk.LEFT)
		entry_rt6[s].pack(side = tk.LEFT)
		button_del_std[s].pack(side = tk.LEFT)
		entry_composi6[s].pack(side = tk.LEFT)
		entry_valence6[s].pack(side = tk.LEFT)
		button_calc6[s].pack(side = tk.LEFT)
		
		entry_mz6[s].bind("<KeyRelease>", func = activate_input_std)		# 文字入力窓への入力に反応するイベント
		entry_name6[s].bind("<KeyRelease>", func = activate_input_std)
		entry_rt6[s].bind("<KeyRelease>", func = activate_input_std)
		entry_composi6[s].bind("<KeyRelease>", func = activate_input_std)
		entry_valence6[s].bind("<KeyRelease>", func = activate_input_std)
		entry_composi6[s].bind("<Return>", func = make_calculate_entrykey(s))		# return に反応。個別に反応する仕掛け
		
		subframe6[s].pack(side = tk.TOP, anchor = tk.W)
	button_addnewstd.pack(side = tk.LEFT)		# リストに下に置くボタンを再表示。これできちんと下に来る
	label_std_message.pack(side = tk.LEFT)
	ping_std = 1
	
# フレーム６へのユーザー入力に反応する関数。何故か引数を一個受け取ることにしないとエラーになる。
def activate_input_std(dammy):
	global standard_mz
	global standard_calib
	global standard_name
	global standard_rt
	global standard_composi
	global ping_std
	for s in range(0, len(label_order6)):
		standard_mz[s] = floating(standard_mz_var[s].get() )	# float型の入力にしてsetする
		standard_rt[s] = floating(standard_rt_var[s].get() )
		standard_mz_var[s].set(standard_mz[s])
		standard_rt_var[s].set(standard_rt[s])
		standard_calib[s] = standard_check_var[s].get()		# 入力を変数に反映する
		standard_name[s] = standard_name_var[s].get()
		standard_composi[s] = standard_composi_var[s].get()
		valence = integering(standard_valence_var[s].get(), '')	# 価数はint型。int型にする関数作ったし使おう
		if(valence == 0):valence = 1
		standard_valence[s] = valence
		standard_valence_var[s].set(valence)
	ping_std = 1
def activate_checkbutton_std():
	activate_input_std(0)		# チェックボタンはコールバックcommandなので引数を渡せない。ダミー引数を渡すだけの関数

# ユーザー入力文字列をfloatに変換する関数
def floating(strings):
	strings = re.sub(r'[^0-9\.]', '', strings)	# 数字か小数点以外の文字が入っていたら取り除く
	if(strings.count('.') > 1):				# 小数点が２個以上ある場合。
		output = re.search(r'\.', strings)
		pos = output.start()	# 最初の小数点を境に右部分から小数点を取り除いて連結する
		left = strings[:pos+1]
		right = strings[pos+1:]
		right = re.sub(r'\.','', right)
		strings = left + right
		strings = float(strings)
	if(strings == ''):
		strings = 0.0
	return(strings)

# フレーム６のcalculateボタンの反応。ボタンのコールバックcommandから引数つきで呼ぶためにクロージャ関数を使う。
def calculate_mz(num):
	
	# 正規表現で処理してみる
	formula = '^C[0-9]*H?[0-9]*N?[0-9]*O?[0-9]*P?[0-9]*S?[0-9]*(Na)?[0-9]*K?[0-9]*(Cl)?[0-9]*(Br)?[0-9]*'
	main_formula = re.compile(r'%s$' % formula)				# イオンの入力が無い場合の判定に使う
	expand_formula = re.compile(r'%s[\+\-]' % formula)		# イオンの入力がある場合の判定に使う。何故か[$\+\-]は機能しない
	ion_formula = re.compile(r'(Na)?[0-9]*K?[0-9]*(Cl)?[0-9]*(Br)?[0-9]*C?[0-9]*H?[0-9]*N?[0-9]*O?[0-9]*P?[0-9]*S?[0-9]*')
	fragment_formula = re.compile(r'C?[0-9]*H?[0-9]*N?[0-9]*O?[0-9]*P?[0-9]*S?[0-9]*(Na)?[0-9]*K?[0-9]*(Cl)?[0-9]*(Br)?[0-9]*')
	flag = 'OK'
	compound = ''	# メイン化合物の組成式
	ion = []	# 増減分の組成式。  メイン化合物 +/- アダクトイオン or フラグメント +/-...のような書き方を想定しよう
	code = []	# １かマイナス１。なお、2+ とかそういうのは対応外としておく。面倒だから。
	
	strings = standard_composi_var[num].get()	# 入力を得る。standard_composi[num]への登録は<KeyRelease>で別途行われる
	strings = re.sub(' ','',strings)	# まず空白を消す。
	
	# メインの組成式を取り出す。
	if(re.search(r'[^0123456789CHNOSP(Na)K(Cl)(Br)\+\-]',strings)):	# 想定外の文字が混ざってないかチェック
		flag = 'unexpcted letter(s)'
	if(flag == 'OK'):
		formula_check = 0		# 文字チェックをパスしたら組成式の入力が正しいかチェックする
		if(main_formula.match(strings)):
			formula_check = 1
			compound = main_formula.match(strings).group()
		if(expand_formula.match(strings)):
			formula_check = 1
			compound = re.match(r'%s' %formula, strings).group()	# +/- は要らないので。
		if(formula_check == 0):
			flag = 'invalid syntax'
		print(strings, compound)
	
	# イオンの組成式を取り出す
	if(flag == 'OK'):
		if(re.match(r'%s[\+\-]' % compound, strings)):	# 化学式に続いて+か-で区切ってある場合
			spl = re.split(r'[\+\-]', strings)
			for s in range(1,len(spl)):
				ion.append(spl[s])
			if(spl[-1] == ''):				# 最後に+か-を書いたときは空白
				spl.pop(-1)
			for i in range(0,len(ion)):			# 同じイオンを複数書いたときはエラーとする。
				for j in range(i+1, len(ion)):
					if(ion[i] == ion[j]):
						flag = 'duplicate ion' + ion[i]
						break
			for i in range(0,len(ion)):			# 符号は + か - か調べる
				c = re.search(r'[\+\-]%s' % ion[i], strings).group()	# ion部分の文字列の前に+/-があるはず
				if(c[0] == '+'):code.append(1)
				if(c[0] == '-'):code.append(-1)
			for i in range(0,len(ion)):			# イオンの中がそれっぽくなかったらエラーとする。
				ion[i] = re.sub('CH3COOH','C2H4O2',ion[i])	# 酢酸	ありそうな入力ミスは対応しておく。H2OはこのままでOK
				ion[i] = re.sub('CH3COO','C2H3O2',ion[i])	# 酢酸イオンネガティブイオンモード
				ion[i] = re.sub('NH4','H4N',ion[i])			# アンモニウムイオン
				ion[i] = re.sub('NH3','H3N',ion[i])			# アンモニウムネガティブイオンモード
				ion[i] = re.sub('HCOOH','CH2O2',ion[i])		# ギ酸
				ion[i] = re.sub('HCOO','CHO2',ion[i])		# ギ酸アダクトネガティブイオンモード
				ion[i] = re.sub('CH3CN','C2H3N',ion[i])		# アセトニトリル
				if(code[i] == (-1)):	# フラグメント化で減った場合の判定。-の項に Clと Naが入ったらエラーになる。まぁいいか。。
					if(ion[i] != fragment_formula.match(ion[i]).group()):
						print(ion[i], fragment_formula.match(ion[i]).group())
						flag = 'invalid fragment ' + ion[i]
						break
				if(code[i] == 1):		# アダクトの場合。ClがCより先に来ることってあるのかな。
					if(ion[i] != ion_formula.match(ion[i]).group()):
						print(ion[i], ion_formula.match(ion[i]).group())
						flag = 'invalid adduct ' + ion[i]
						break
	
	# m/zを計算する。
	if(flag=='OK'):	# 判定をパスした場合
		compound_weight = 0.0
		element = ['C','H','N','O','P','S','Na','K','Cl','Br']
		eweight = [12.000000, 1.007825, 14.003074, 15.994914, 30.973761, 31.972071, 22.989769, 38.963706, 34.968852, 78.918337]
		for i in range(0, len(element)):
			compound_weight += eweight[i] * calc_mw(element[i], compound)
		print(compound, compound_weight)
		ion_weight = []
		for i in range(0, len(ion)):
			ion_weight.append(0.0)
			for j in range(0, len(element)):
				ion_weight[i] += eweight[j] * calc_mw(element[j], ion[i])
		for i in range(0, len(ion)):
			compound_weight += ion_weight[i] * code[i]
			print(ion[i], ion_weight[i], code[i])
		print()
		compound_weight = int(compound_weight * 1000000)/1000000	# 何故か無駄な小数点以下の数が発生するので対応する
		
		standard_mz[num] = compound_weight
		standard_mz_var[num].set(compound_weight)
		
		button_calc6[num].configure(text = 'calculate m/z', fg='SystemTextColor')
	else:
		button_calc6[num].configure(text = flag, fg='#FF0000')
		return
def make_calculate(n):
	def calc_():
		calculate_mz(n)
	return calc_
def make_calculate_entrykey(n):
	def calc_(dammy):	# Entryの<Return>にbindするときは何故かここにdammy引数が必要
		calculate_mz(n)
	return calc_

# 元素の数を返す関数
def calc_mw(element, compound):
	if(re.search(r'%s' % element, compound)):	# まずその元素があるか調べる
		if(re.search(r'%s[0-9]+' % element, compound)):		# 数字が１文字以上書いてある場合はそれが答え
			c = re.search(r'%s[0-9]+' % element, compound).group()
			n = re.search(r'[0-9]+', c).group()
			return(int(n))
		else:	# 元素文字の次が数字じゃなかったとき
			if(re.search(r'%s$' % element, compound)):		# C/Nで終わる場合は次でエラーなので最後判定が必要
				return(1)		# 最後の文字だった場合は１個
			if(element == 'C'):		# CのときはClである可能性がある
				if(re.search(r'C.', compound).group() == 'Cl'):
					return(0)
				else:
					return(1)
			if(element == 'N'):		# NのときはNaである可能性がある
				if(re.search(r'N.', compound).group() == 'Na'):
					return(0)
				else:
					return(1)
			return(1)	# CNの判定じゃないし、最後でもなく、数字が書いてない場合は１個
	else:
			return(0)	# 元素記号が書かれてなかった場合は0個

#def resize(dammy):
#	vx, vy = scrollbar_v.get()
#	hx, hy = scrollbar_h.get()
#	scrollbar_v.set(vx, vy)
#	scrollbar_h.set(hx, hy)

def close_self():
	os._exit(0)

##############################
#       GUI のレイアウト
##############################

# Tkinter のメインウィンドウ
root = tk.Tk()
root.title('GrassHopper Manager: ' + project)
root.geometry('800x500')
#root.bind('<Configure>', resize)

# メニューバー
menubar = tk.Menu(root)
root.config(menu = menubar)
menu_file = tk.Menu(root)
menubar.add_cascade(label='file', menu = menu_file)
menu_file.add_command(label='load project', command=load_project)
menu_file.add_command(label='save (overwrite)', command=save_project)
menu_file.add_command(label='save as new', command=input_savefilepass)
menu_file.add_command(label='add new files (ProteoWizard output text)', command=load_project)
menu_file.add_command(label='call GrassHopper', command=call_grasshopper)
menu_file.add_separator()
menu_file.add_command(label='close', command=close_self)

# 画面全体にスクロールバーを設置。rootをcanvasで埋めてbarを付け、さらにframeで埋める。（rootやframeにbarは付かない）
canvas = tk.Canvas(root)							# 全体をキャンバスで埋める。frameにはbarを設置できないため
canvas.config(scrollregion = (0,0,800,5000))			# canvasのサイズ。動的にしたいんだけど
canvas.grid(row = 0, column = 0, sticky = tk.N+tk.E+tk.W+tk.S)	# packだと縦横スクロールバーが右下で重なるのでgridにする
scrollbar_h = tk.Scrollbar(root, orient = tk.HORIZONTAL)	# barを設定
scrollbar_v = tk.Scrollbar(root, orient = tk.VERTICAL)
scrollbar_v.grid(row=0, column=1, sticky = tk.N+tk.S)		# barはgridでとなりのマスに配置
scrollbar_h.grid(row=1, column=0, sticky = tk.E+tk.W)
scrollbar_v.config(command = canvas.yview)				# bar のcommandをcanvasのyview
scrollbar_h.config(command = canvas.xview)
canvas.config(yscrollcommand = scrollbar_v.set)			# canvas 側でもbarをyscrollに設定
canvas.config(xscrollcommand = scrollbar_h.set)
rootframe = tk.Frame(canvas)				# root扱いにするframeを設定し、canvas内でcreatewindowする
canvas.create_window((0,0), window=rootframe, width=800, height=5000, anchor=tk.NW)
root.grid_rowconfigure(0, weight = 1)
root.grid_columnconfigure(0, weight = 1)

# フレームを設定
#frame1 =tk.Frame(rootframe, relief = 'groove', bd=1)		# 一番上の行。名前はどうかと思うがとりあえず適当に。
frame1 =tk.Frame(rootframe)		# 一番上の行。名前はどうかと思うがとりあえず適当に。
frame2 =tk.Frame(rootframe)		# ２番めの行。ファイルリストの先頭行。sortのボタンとか
frame3 =tk.Frame(rootframe)		# ３番目の行。ファイルリストを表示する。ラジオボタンとか。
frame4 =tk.Frame(rootframe, relief = 'groove', bd=1)		# ４番目の行。標品データのファイルをロードしたりセーブしたり
frame5 =tk.Frame(rootframe)		# ５番目の行。標品データのリストの先頭行。sortボタンとか
frame6 =tk.Frame(rootframe)		# ６番目の行。標品データのリスト
frame7 =tk.Frame(rootframe, relief = 'groove', bd=1)		# ７番目の行。
frame8 =tk.Frame(rootframe)		# ８番目の行。
frame9 =tk.Frame(rootframe)		# ９番目の行。

# フレーム１、プロジェクトをセーブするボタンとかGrassHopperを呼ぶボタンとか
button_load = tk.Button(frame1, text = 'Load Project', command = load_project).pack(side = tk.LEFT)
button_save = tk.Button(frame1, text = 'Save', command = save_project).pack(side = tk.LEFT)
button_saveas = tk.Button(frame1, text = 'Save As', command = input_savefilepass).pack(side = tk.LEFT)
button_call = tk.Button(frame1, text = 'Call GrassHopper', fg = 'blue', command = call_grasshopper)
button_call.pack(side = tk.LEFT)
message_frame1 = 'Project Name: ' + project
message_frame1_label = tk.StringVar()
message_frame1_label.set(message_frame1)
label_message_frame1 = tk.Label(frame1, textvariable = message_frame1_label).pack(side = tk.LEFT)
frame1.pack(side = tk.TOP, anchor = tk.NW)

# フレーム２、ファイルリストの先頭行
label_order = tk.Label(frame2, text = 'order', width = 4, anchor = tk.CENTER).pack(side = tk.LEFT)
label_vender = tk.Label(frame2, text = 'vender', width = 6, anchor = tk.CENTER).pack(side = tk.LEFT)
button_sort = tk.Button(frame2, text = 'Sort', width = 26, command = sort_filelist).pack(side = tk.LEFT)
label_radio = tk.Label(frame2, text = 'show/hide', width = 8, anchor = tk.CENTER).pack(side = tk.LEFT)
button_factor = tk.Button(frame2, text = 'factor', width = 3, command = sort_by_factor).pack(side = tk.LEFT)
label_color = tk.Label(frame2, text = 'manual', width = 8, anchor = tk.CENTER).pack(side = tk.LEFT)
label_select = tk.Label(frame2, text = 'color select', width = 9, anchor = tk.CENTER).pack(side = tk.LEFT)
frame2.pack(side = tk.TOP, anchor = tk.W)
space_frame2 = tk.Frame(rootframe)	# フレーム２の前に隙間をあける
space_frame2_label = tk.Label(space_frame2, text = '*** Data files to Analyze by GrassHopper ***').pack()
space_frame2.pack(before = frame2, anchor = tk.CENTER)

# フレーム３、ファイルのリスト
subframe3 = []
label_order3 = []
label_files = []
button_del = []
radiobutton_fileshow_var = []
radiobutton_showswitch1 = []
radiobutton_showswitch2 = []
radiobutton_colorswitch_var = []
radiobutton_colorswitch1 = []
radiobutton_colorswitch2 = []
radiobutton_colorswitch3 = []
label_vender = []
entry_color = []
manualcolor_var = []
factorlist_var = []
entry_factor = []
button_addnewfile = tk.Button(frame3, text = 'add new file(s)', width = 55, command = add_filelist)	# これはただの初期値。まだpackしない
refresh_frame3()
frame3.pack(side = tk.TOP, anchor = tk.W)

# フレーム４、標品データのロード＆セーブボタン
button_load_std = tk.Button(frame4, text = 'import standard file from other project').pack(side = tk.LEFT)
button_save_std = tk.Button(frame4, text = 'save as standard file').pack(side = tk.LEFT)	# いらない気がする。
#frame4.pack(side = tk.TOP, anchor = tk.NW)
space_frame4 = tk.Frame(rootframe)	# フレーム４の前に隙間をあける
space_frame4_label = tk.Label(space_frame4, text = '***  Standard Compounds for m/z calibration / compound label  ***').pack()
#space_frame4.pack(before = frame4, anchor = tk.CENTER)

# フレーム５、標品リストの先頭行
label_number = tk.Label(frame5, text = '', width = 2, anchor = tk.CENTER).pack(side = tk.LEFT)
label_mz = tk.Label(frame5, text = 'm/z', width = 3, anchor = tk.CENTER).pack(side = tk.LEFT)
button_sort_std = tk.Button(frame5, text = 'Sort', width = 3, command = sort_stdlist).pack(side = tk.LEFT)
label_composition = tk.Label(frame5, text = 'use', width = 4, anchor = tk.CENTER).pack(side = tk.LEFT)
label_name = tk.Label(frame5, text = 'Compound Name', width = 14, anchor = tk.CENTER).pack(side = tk.LEFT)
label_rt = tk.Label(frame5, text = 'Expected Rt', width = 12, anchor = tk.W).pack(side = tk.LEFT)
label_composition = tk.Label(frame5, text = 'Component ex.C14H15NO2+NH4-H2O', width = 36, anchor = tk.W).pack(side = tk.LEFT)
frame5.pack(side = tk.TOP, anchor = tk.W)

# フレーム６、標品リスト
subframe6 = []
label_order6 = []
standard_mz_var = []
standard_name_var = []
standard_rt_var = []
standard_check_var = []		# チェックボックスなのでbooleanVar
standard_composi_var = []
standard_valence_var = []
entry_mz6 = []
entry_name6 = []
entry_rt6 = []
checkbutton_calib6 = []
entry_composi6 = []
entry_valence6 = []
button_calc6 = []
button_del_std = []
button_addnewstd = tk.Button(frame6, text = 'add empty line', command = add_new_std)	# 変数宣言に伴う初期値。まだpackしない。
label_std_message = tk.Label(frame6, text = 'm/z value is essential')
refresh_frame6()	# 一回呼ぶ
frame6.pack(side = tk.TOP, anchor = tk.W)

# フレーム７、ライブラリをロードしたりセーブしたり
button_loadlibrary = tk.Button(frame7, text = 'load library').pack(side = tk.LEFT) #, command = save_library)
button_saveaslibrary = tk.Button(frame7, text = 'save as library').pack(side = tk.LEFT) #, command = save_library)
#frame7.pack(side = tk.TOP, anchor = tk.W)
space_frame7 = tk.Frame(rootframe)	# フレーム４の前に隙間をあける
space_frame7_label = tk.Label(space_frame7, text = '***  Peak Location  ***').pack()
#space_frame7.pack(before = frame7, anchor = tk.CENTER)

# フレーム８、ライブラリのリスト
label_rt_start = tk.Label(frame8, text = 'Rt(start)').pack(side = tk.LEFT)
label_rt_end = tk.Label(frame8, text = 'Rt(end)').pack(side = tk.LEFT)
label_mz_center = tk.Label(frame8, text = 'm/z').pack(side = tk.LEFT)
label_mz_width = tk.Label(frame8, text = 'm/z(range)').pack(side = tk.LEFT)
label_mz_name = tk.Label(frame8, text = 'Compound name').pack(side = tk.LEFT)
#frame8.pack(side = tk.TOP, anchor = tk.W)

button_addlibrary = tk.Button(frame9, text = 'add new line').pack(side = tk.LEFT) #, command = add_new_lib)
#frame9.pack(side = tk.TOP, anchor = tk.W)

loadmode = 'init'
load_project()

thread1 = threading.Thread(target = load_ping)
thread1.setDaemon(True)
thread1.start()


root.mainloop()
