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

print('python loaded')
import os	# フォルダ情報の取得と、os._exit(0)でないとGLUTから抜けられないので
import sys	# GLUTの書き方に sys.srgv というのがあったから
import math	# 円周率とか。
from OpenGL.GL import *		# OpenGL。pyopenglモジュールは別途インストールする必要がある
from OpenGL.GLU import *	# 視点の設定などに使う
from OpenGL.GLUT import *	# 描画ウインドウを作るのに使う
import numpy as np	# openGLの描画データをGPUにわたすために必要
import time		# デモモードに入る時間を測る
#import random	# デモモードでランダムに動くのに使う
import re	# 正規表現
import threading	# マルチスレッド。重たい関数呼び出しをバックグラウンド化。残念なことにCPUコアを２つ使うことはできない
# import multiprocessing	# 別のCPUコアを使って別のプログラムを起動するもの。Poolというメソッドを使うといい感じらしい？

print('modules loaded')

project = ''
projectfilepass = ''
datafilepass = ''
exportfilepass = ''
pingfilepass = ''

def argv():
	global project
	global projectfilepass
	global datafilepass
	global exportfilepass
	global pingfilepass
	argv = sys.argv
	projectfilepass = argv[1]
	p = projectfilepass.split('/')	# この変数が気に入らない。
	project = p[-1][0:-4]
	datafilepass = projectfilepass[0:-4] + '.dat'
	pingfilepass = projectfilepass[0:-4] + '.ping'
	exportfilepass = projectfilepass[0:-4] + '.txt'

filename = []		# filename[f] = ファイル名
file_color_vivid = []		# 表示色。デフォ値を用意しておく。明るい方
file_color_trans = []		# 表示色。デフォ値を用意しておく。透けてる方
file_timefactor = []		# ファイル名の中から実験時刻の情報をみつけたとき入れとく。
vendername = []		# vendername[f] = LCMS会社の記号。waters=0, thermo=1, sciex=2
vender = ['waters','thermo','sciex']
files = 0			# データファイルの数
data_rt = []		# data_rt[f][sign] = リテンションタイム。輝度順に並んでいる
data_mz = []		# data_mz[f][sign] = m/z値。輝度順に並んでいる
data_it = []		# data_it[f][sign] = シグナル輝度。輝度順に並んでいる
data_signs = []		# data_signs[f] = ファイルに含まれるシグナルの数。

data_rt_bkup = []
data_mz_bkup = []

maxrt = 0.0	#  Rt の最大値 表示枠の軸のスケールに使う
maxmz = 0.0	#  m/zの最大値 表示枠の軸のスケールに使う
maxit = 0.0	#  it の最大値 venderでスケールがケタ違うが、いい感じのときもあるようだ。ユーザー設定かな？

show_files = 3	# 同時表示するサンプルの数。重たいときに制限をかけるためのもの。
show_peaks_switch = 1	# 選択したピークを明るく表示する機能をオンオフする。1 で表示、0で非表示

calibration_mza = []	# calibration_mza[f] １次関数の係数。１点補正のときはゼロ。補正後 m/z = 生m/z値 +a(生m/z値)+b
calibration_mzb = []	# calibration_mzb[f] １次関数のY切片。１点補正のときはこれだけ有効。ファイルごと
calibration_rta = []	# calibration_rta[f] １次関数の係数。Rtの微調整用。同上
calibration_rtb = []	# calibration_rtb[f] １次関数のY切片。Rtの微調整用。同上
calibration_rt_largea = []			# cal..[f] １次関数の係数。大きな補正をするときのためのもの。同上
calibration_rt_largeb = []			# cal..[f] １次関数の係数。大きな補正をするときのためのもの。大きな補正は先にやる
calibration_rt_large_flag = []		# cal..[f] 大きな補正をするファイルを示すフラグ

# メインデータをロードする。４行で１ファイル分。ファイル名vender記号、Rt、m/z、itの順。シグナルはit順でソートされたもの
def data_loader():
	global filename
	global file_color_vivid
	global file_color_trans
	global vendername
	global files
	global data_rt
	global data_mz
	global data_it
	global data_rt_bkup
	global data_mz_bkup
	global data_signs
	global maxrt
	global maxmz
	global maxit
	global show_files
	
	# データがあるか探す。
	savefile_flag = 0
	if(os.path.isfile(datafilepass)):
		savefile_flag = 1
		print('datafile Found: ', datafilepass)
	else:
		print('datafile Not found: ', datafilepass)
		os._exit(0)
	if(savefile_flag == 0):		# 無かったら何もせずにreturn
		return
	
	st = time.time()
	# ロード開始
	if(savefile_flag == 1):
		filename.clear()		# データファイルは壊れていないものとしてここで変数を初期化
		vendername.clear()
		file_timefactor.clear()
		files = 0
		data_rt.clear()
		data_mz.clear()
		data_it.clear()
		data_signs.clear()
		maxrt = 0.0
		maxmz = 0.0
		maxit = 0.0
		maxit_vender = (-1)
		
		filehandle = open(datafilepass)
		whole_data = filehandle.read()		# まるごとロード
		filehandle.close()
		print('datafile loaded, processing...')
		
		s = whole_data.split('\n')	# 改行でsplit。改行は取り除かれる。便利
		files = int(len(s)/4)		# ４行で１ファイルなので４で割ったら丁度ファイル数になるはず
		if(show_files > files):
			show_files = files		# 同時表示するファイルの数の設定値がファイル数を超えているとエラーなので最大値に戻す
		for f in range(0,files):
			if(s[f*4+0] == ''): break
			sf = s[f*4+0].split(',')
			rt = s[f*4+1].split(',')	# splitの出力は文字列のリスト
			mz = s[f*4+2].split(',')
			it = s[f*4+3].split(',')
			rt_float = list(map(float, rt))		# 文字列をfloatに変換。=[float(n) for n in rt] より有意に速い
			mz_float = list(map(float, mz))		# リスト内包表記より=np.array(rt, dtype = np.float32).tolist() の方が速い
			it_float = list(map(float, it))		# ここでnumpy型にしておくよりlistで持つ方が後の処理が圧倒的に速い
			data_rt.append(rt_float)	# float型に変換してからリストに追加。
			data_mz.append(mz_float)
			data_it.append(it_float)
			data_rt_bkup.append(rt_float)		# calibrationのやり直しのためにバックアップする
			data_mz_bkup.append(mz_float)		# これでコピーできているのか不明。参照渡しになっていそうだけどなぜか機能する。
			filename.append(sf[0])
			vendername.append(int(sf[1]))
			data_signs.append(len(rt))	# ロードしたMSシグナルの数
			mxrt = max(rt_float)	# 最大値を計算しておく
			mxmz = max(mz_float)
			mxit = max(it_float)
			if(maxrt < mxrt):maxrt = mxrt
			if(maxmz < mxmz):maxmz = mxmz
			if(maxit < mxit):
				maxit = mxit
				maxit_filenum = f
			
			print(filename[f],vender[vendername[f]],'\t',data_signs[f],'\t',mxit)
	print(maxrt,maxmz,maxit,'\nmax intensity contained in:', filename[maxit_filenum])
	print('load: ',time.time()-st)
	
	# とりあえずの色を割り当てておく。これで区別不能の無色にはならない。
	for f in range(0,files):
		val = f / files		# ファイル番号を使って緑から赤までのグラデーションを割り当てる
		r = 1.0 * val
		g = 1.0 * (1.0 - val)
		b = 0.0
		file_color_vivid.append([r,g,b])		# なぜかglobalしなくても書き込みできる。
		file_color_trans.append([r,g,b,0.5])
	
	# タイムファクターも一応探しておく。あったやつだけ上書き。
#	timefactors = 0
#	timefactor = []
#	file_timefactor = [0] * files
#	for f in range(0,files):	# まずタイムファクターを持つファイルが何個あるか探す。
#		if(re.search(r'[0-9]+day',filename[f])):
#			day = re.search(r'[0-9]+day',filename[f])
#			days = re.search(r'[0-9]+', day.group())
#			timefactor.append(float(days.group()))
#			timefactors += 1
#	if(timefactors > 1):	# タイムファクターを持つファイルが複数あった場合のみ有効。
#		mx = max(timefactor)
#		mn = min(timefactor)
#		for f in range(0,files):
#			if(re.search(r'[0-9]+day',filename[f])):
#				day = re.search(r'[0-9]+day',filename[f])
#				days = re.search(r'[0-9]+', day.group())
#				file_timefactor[f] = days.group()		# 色を上書きするついでにタイムファクター自体も保存する。文字列型のままでひとまず。
#				val = (float(days.group()) -mn) / (mx-mn)
#				r = 1.0 * val
#				g = 1.0 * (1.0 - val)
#				b = 0.0
#				file_color_vivid[f]=[r,g,b]
#				file_color_trans[f]=[r,g,b,0.5]
	
#data_loader()	# 一回呼ぶ。テスト

# ユーザー入力の表示色と標品データをロード

#show_file_color = []	# ファイルに色を指定する。引数はshow_file に入れる引数。ファイル番号じゃなかった。
intensity_scale = 10	# 空の高さのユーザー設定値
show_file = []	# ファイル番号を返すリスト。どのファイルにするかはstandards ファイルの上から順にユーザーが指定の数分のリスト
file_magnify = []	# ファイルごとのカスタムな表示倍率
standard_mz = []	# 標品のm/z ユーザー設定
standard_rt = []	# 標品のm/z ユーザー設定
standard_label = []	# 標品のラベル。ユーザー指定
standard_cflag = []	# 標品のフラグ
standards = 0		# 標品の数。

def load_standards():
	
	global show_files
	global intensity_scale
	global show_file
	global file_color_vivid
	global file_color_trans
	global standard_mz
	global standard_rt
	global standard_label
	global standard_cflag
	global standards
	global file_magnify
	global file_timefactor
	
	# まずユーザー入力ファイルが存在するかチェック
	savefile_flag = 0
	if(os.path.isfile(projectfilepass)):
		savefile_flag = 1
		print('projectfile Found: ', projectfilepass)
	else:
		print('projectfile Not found: ', projectfilepass)
		os._exit(0)
	if(savefile_flag == 0):		# 無かったら何もせずにreturn
		return
		
	
	# 存在する場合は更新される情報を一旦クリアしてロードを試みる
	if(savefile_flag == 1):
		show_files = 0
		show_file.clear()
		intensity_scale = 10
		file_magnify.clear
		file_magnify = [1.0]*files	# 色は順番に並んでないので初期化する必要あり
		standard_mz.clear()
		standard_label.clear()
		standard_cflag.clear()
		standards=0
		
		filehandle = open(projectfilepass)
		
		line0 = filehandle.readline()	# １行目はダミー
		line1 = filehandle.readline()	# ２行目もダミー。##は表示ファイル数の設定
		intensity_scale = 10
			
		# ３行目以降はファイル名とか色とか。
		loop_flag = 0	# 次の標品データに突入したフラグ
		show_count = 0	# show_files に達するまで登録し続けるためのカウンター
		while(loop_flag == 0):
			line = filehandle.readline()
			line = line.replace('\n','')
			
			# まず終了しているか調べる
			if(line == ''):break			# ファイルの末尾だったら強制的にbreak
			lin = line.split('\t')
			if(lin[0] == 'Expected m/z'):	# 終わりの目印はこの文字列にしよう
				loop_flag = 1
				break
			
			# データ中のファイル名のどれにあたるかを判定する。無い場合は(-1)
			filenum = (-1)
			for f in range(0,files):
				d = lin[0].split('/')
				datafilename = d[-1]
				if(filename[f] == datafilename):	# データ中に該当名前のファイルがあるか調べる
					filenum = f
					break
			
			# 無事にデータ中のファイル名と照合できたら表示指定の配列に登録して色と拡大率のデータを格納する
			if(filenum > (-1)):
				# 同時表示のユーザー指定をファイルリストに反映する
				if(lin[3] == '1'):
					show_file.append(filenum)
					show_count += 1
					show_files += 1
				
				# ズーム値。使うかもしれない使わないかも知れない
				if(len(lin) > 3):		# ユーザー指定データが壊されててもエラーで止まらないようにする
					# ズーム値。
					file_magnify[filenum] = 1.0
					file_timefactor.append(int(lin[4]))
				
				# 色
				col = hex2color('')
				if(len(lin) > 2):
					col = hex2color(lin[2])
				file_color_vivid[filenum] = [col[0], col[1], col[2]]
				file_color_trans[filenum] = [col[0], col[1], col[2], 0.5]
					
			else:	# ユーザー設定ファイルにあるファイル名がデータ中にない場合（エラーですが）
				print('data for file ', lin[0], 'is NOT FOUND')# 該当データを表示しない
		
		# 次は標品のデータ
		while(loop_flag==1):		# 標品m/zデータのある所まで来た目印を無事にみつけた場合の判定を兼ねてみる
			line = filehandle.readline()
			line = line.replace('\n','')
			if(line == ''):
				loop_flag=0
				break

			lin = line.split('\t')
			standard_mz.append(float(lin[0]))
			try:
				standard_label.append(lin[1])
			except:
				standard_label.append('')
			try:
				standard_rt.append(float(lin[2]))
			except:
				standard_rt.append(0.0)
			try:
				if(lin[3] == '1'):
					standard_cflag.append(1)
				else:
					standard_cflag.append(0)
			except:
				standard_cflag.append(0)
			standards += 1

# 16進数を色に変換する関数
preset_colors = 15		# 色指定を文字で書いてもいいようにしておく
preset_color = [	['red',		0xFF0000],
					['green',	0x00FF00],
					['skyblue',	0x00FFFF],
					['blue',	0x0000FF],
					['yellow',	0xFF7700],
					['orange',	0xFFFF00],
					['purple',	0xFF00FF],
					['black',	0x000000],
					['gray',	0x777777],
					['darkred',	0x770000],
					['darkgreen',	0x007700],
					['darkblue',	0x000077],
					['darkorange',	0x777700],
					['darkpurple',	0x770077],
					['gray',	0x777777],
					['white',	0xFFFFFF]	]
def hex2color(val):
	
	match = re.search(r'[0-9A-Fa-f]{6}', val)	# 入力値の中にある６桁の16進数をint型に変換する
	if(bool(match)):
		col = str.upper(match.group(0))
		val = int('0x'+ col, 0)
	else:							# ６桁の16進数が無かった場合は
		flag = 1
		for i in range(0, preset_colors):		# 色名を文字で書いてあった場合はhexに変換
			if(val == preset_color[i][0]):
				val = int(preset_color[i][1])
				flag = 0
				break
		if(flag == 1):
			val = 0x00FFFF	# それ以外は全部水色に設定してみる
		
	r = int(val/256/256)
	g = int((val-r*256*256)/256)
	b = (val -r*256*256 -g*256)
	r /= 256
	g /= 256
	b /= 256
	return([r,g,b])

# projectファイルが変更されたとき
def reset_by_project():
	global filename
	global file_color_vivid
	global file_color_trans
	global vendername
	global file_timefactor
	global files
	global data_rt
	global data_mz
	global data_it
	global data_rt_bkup
	global data_mz_bkup
	global data_signs
	global show_files
	global show_file
	global file_magnify
	global maxrt
	global maxmz
	global maxit
	global maxit_filenum
	
	show_file.clear()
	show_files=0
	file_magnify.clear()
	file_color_vivid.clear()
	file_color_trans.clear()
	data_rt_bkup.clear()
	data_mz_bkup.clear()
	file_timefactor.clear()
	
	# データファイル使うかどうかわからないけどロードしておく
	savefile_flag = 0
	if(os.path.isfile(datafilepass)):
		savefile_flag = 1
		print('datafile Found: ', datafilepass)
	if(savefile_flag == 0):		# 無かったら何もせずにreturn
		print('datafile Not found: ', datafilepass)
		os._exit(0)
	filehandle = open(datafilepass)
	whole_data = filehandle.read()		# まるごとロード。一瞬でできるから。
	filehandle.close()
	whole_data_split = whole_data.split('\n')	# 改行でsplit。改行は取り除かれる。便利
	print(datafilepass + ' loaded, processing...')
	
	# プロジェクトファイルから情報を取り出す
	maxit_filename = 'previous files'
	if(os.path.isfile(projectfilepass)):	# プロジェクトファイルを読みに行く
		print('projectfile Found: ', projectfilepass)
		filehandle = open(projectfilepass)
		line0 = filehandle.readline()	# １行目２行目はダミー
		line1 = filehandle.readline()	# ３行目からファイル名とか並んでる
		
		# 今あるデータを複製するものは別の配列に一時保存
		new_filename = []	# 新しい順番のリスト。最後にコピーしてできあがり
		new_vendername = []
		new_data_rt = []
		new_data_mz = []
		new_data_it = []
		new_data_signs = []
		new_files = 0
		
		loop_flag = 0	# 次の標品データに突入したフラグ
		while(loop_flag == 0):
			line = filehandle.readline()
			line = line.replace('\n','')
			
			# まず終了しているか調べる
			if(line == ''):break			# ファイルの末尾だったら強制的にbreak
			lin = line.split('\t')
			if(lin[0] == 'Expected m/z'):	# 終わりの目印はこの文字列にしよう
				loop_flag = 1
				break
			
			# データのある行だったときは情報を配列にセットする
			if(lin[3] == '1'):		# ４番目はshow/hide
				show_file.append(new_files)
				show_files += 1
				
			col = hex2color(lin[2])	# ３番目は色
			file_color_vivid.append( [col[0], col[1], col[2] ] )
			file_color_trans.append( [col[0], col[1], col[2], 0.5] )
			
			file_magnify.append(1.0)	# ８番目lin[7]。まだ使ってないが縦軸をマニュアル調整する値
			file_timefactor.append(int(lin[4]))	# ５番目はタイムファクター
			
			# ファイル名。ファイルが既存かどうか調べる
			d = lin[0].split('/')
			new_filename.append(d[-1])
			
			# ファイル名に相当するデータを探す
			newf = d[-1]
			num = (-1)
			for f in range(0, files):
				if(filename[f] == newf):
					num = f
					break
			if(num>(-1)):	# 既にロード済みだった場合は変換済みのデータをコピーする
				new_data_rt.append(data_rt[num])
				new_data_mz.append(data_mz[num])
				new_data_it.append(data_it[num])
				new_vendername.append(vendername[num])
				new_data_signs.append(data_signs[num])
			else:			# 新しいデータだったときは読みに行く
				error_flag = 1
				for f in range(0,int(len(whole_data_split)/4)):		# 行数の1/4がファイル数
					sf = whole_data_split[f*4].split(',')
					if(sf[0] == newf):
						error_flag = 0
						rt = whole_data_split[f*4+1].split(',')	# splitの出力は文字列のリスト
						mz = whole_data_split[f*4+2].split(',')
						it = whole_data_split[f*4+3].split(',')
						rt_float = list(map(float, rt))		# 文字列をfloatに変換。=[float(n) for n in rt] より有意に速い
						mz_float = list(map(float, mz))		# リスト内包表記より=np.array(rt, dtype = np.float32).tolist() の方が速い
						it_float = list(map(float, it))		# ここでnumpy型にしておくよりlistで持つ方が後の処理が圧倒的に速い
						new_data_rt.append(rt_float)	# float型に変換してからリストに追加。
						new_data_mz.append(mz_float)
						new_data_it.append(it_float)
						new_vendername.append(int(sf[1]))
						new_data_signs.append(len(rt))	# ロードしたMSシグナルの数
						mxrt = max(rt_float)	# 最大値を計算しておく
						mxmz = max(mz_float)
						mxit = max(it_float)
						if(maxrt < mxrt):maxrt = mxrt
						if(maxmz < mxmz):maxmz = mxmz
						if(maxit < mxit):
							maxit = mxit
							maxit_filename = newf
						print(new_filename[new_files],vender[new_vendername[new_files]],'\t',new_data_signs[new_files],'\t',mxit)
						break
				if(error_flag == 1):	# データがどっちにもない場合はお手上げ。
					print('error')
					os._exit(0)
			new_files += 1
		filename.clear()
		vendername.clear()
		data_rt.clear()
		data_mz.clear()
		data_it.clear()
		data_rt_bkup.clear()
		data_mz_bkup.clear()
		data_signs.clear()
		for f in range(0,new_files):
			filename.append(new_filename[f])
			vendername.append(new_vendername[f])
			data_rt.append(new_data_rt[f])
			data_mz.append(new_data_mz[f])
			data_it.append(new_data_it[f])
			data_rt_bkup.append(new_data_rt[f])
			data_mz_bkup.append(new_data_mz[f])
			data_signs.append(new_data_signs[f])
		files = new_files
	print(maxrt,maxmz,maxit,'\nmax intensity contained in:', maxit_filename)
	
	load_standards()
	
	# ユーザー指定のライブラリに照合してラベルがあればつけておく。なければブランクのまま
	global library_label
	for l in range(0, len(library_label)):
		std_hit = (-1)
		std_mz_width = 0.3	# 許容幅。両側。
		std_rtdist_min = 100	# Rt が一番近いもの
		calibration_flag = (-1)
		for std in range(0,standards):
			if(abs(standard_mz[std] - library_ave_mz[l]) < std_mz_width):			# m/z値が一致するものの中で
				if(std_rtdist_min > abs(standard_rt[std]-library_draw_rt[l])):
					std_rtdist_min = abs(standard_rt[std]-library_draw_rt[l])		# ピークトップのRtが一番近いもの。m/zが同じで違う化合物。
					std_hit = std
		peak_label = ''
		if(std_hit >(-1)):
			library_label[l] = standard_label[std_hit]
		else:
			library_label[l] = ''
		library_cflag[l] = std_hit
	refresh_librarysignalindex()	# 屏風用のシグナル番号リストを更新する

ping_dat = 0
ping_file = 0
ping_std = 0
ping_export = 0

# Managerにpingを送る
def send_ping():
	pingpass = os.getcwd() + '/' + project +'.ping'	# 複数のGrassHopperを動かすことを想定する。プロジェクト名を鍵にして管理する
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

# Managerからのpingを受け取る
def load_ping():
	global ping_dat
	global ping_file
	global ping_std
#	global ping_export
	while(1):
		pingpass = os.getcwd() + '/' + project +'.ping'	# 複数のGrassHopperを動かすことを想定する。プロジェクト名を鍵にして管理する
		if(os.path.isfile(pingpass)):
			filehandle = open(pingpass)
			dm1 = filehandle.readline()
			line1 = filehandle.readline()
			line2 = filehandle.readline()
			line3 = filehandle.readline()
			filehandle.close()
			
			ping_dat = line1[0]		# データファイルが変更された
			ping_file = line2[0]	# ファイルの色とか順番とかが変更された
			ping_std = line3[0]		# 標品リストが変更された
			ping=0
			if(ping_dat == '1'):
#				data_loader()
#				load_standards()
				ping_dat = '0'
				ping=1
#				send_ping()			# 呼びすぎ
			if(ping_file == '1'):
#				data_loader()
#				load_standards()
				ping_file = '0'
				ping=1
#				send_ping()			# 呼びすぎ
			if(ping_std == '1'):
#				load_standards()
				ping_std = '0'
				ping=1		# テスト用。
#				send_ping()			# 呼びすぎ
			
			if(ping==1):		# テスト。
				ping=0
				reset_by_project()
				set_signal()	# 一回呼ぶ
				set_library()
				send_ping()
				dynamic_zoom()	# __main__で最初に一回呼ぶ
				glutPostRedisplay()
		time.sleep(3)
	


# シグナルをプロットするための座標データ(VBO)を作る
show_signals = 50000				# ファイルごとの表示シグナル数。多すぎると重くなる。waters一回分程度がmaxで500,000個で超重い。3000くらいで概ねOK
show_signals_underlimit  = 3000		# ダミーサンプルのデータとかに表示数が合わさると問題なので最低値を探しておく。
#signal_vertex = np.zeros((files,6*show_signals), dtype = np.float32)	# line(xyz-xyz)なのでシグナルひとつにデータ６つ
signal_vertex = []

field_size = 1.0
field = field_size *2	# シグナルを描画空間内の座標に変換するときなにかとよく使う変数
skyheight = field_size / intensity_scale	# 空の高さ。ユーザー設定値1で地面の幅と同じ。
field_color = [0.0, 0.0, 0.0, 0.0]	# 単色

def set_signal():
	start = time.time()
	global signal_vertex
	global show_signals
	global data_rt
	global data_mz
	global data_it
	global data_signs
	index_min = min(data_signs)
	index_max = max(data_signs)
	if(show_signals > index_min):		# Numpyが真四角のデータを要求するので一番シグナル数が少ないデータに合わせる。NaNで埋められるかどうか試してない
		show_signals = index_min
	if(show_signals < show_signals_underlimit):	# 極端にデータの少ないファイルが混ざってた場合はダミーで埋める。未テスト。これはロード時にやったほうが良いかも？
		for f in range(0,files):
			if(data_signs[f] < show_signals_underlimit):
				dammy = [0] * (show_signals_underlimit - data_signs[f])		# 足りないシグナルをダミーで埋める。座標(rt:mz)=(0:0)に埋め数分。
				data_rt[f] += dammy
				data_mz[f] += dammy
				dammyit = [data_it[f][data_signs[f]-1]] * (show_signals_underlimit - data_signs[f]) # 最小値がゼロよりはるかに大きいのでゼロでなく最小値を使用
				data_it[f] += dammyit
				data_signs[f] = show_signals_underlimit
	signal_vertex.clear()
	for f in range(0,files):
		# スライスしてみる
		max_intensity = max(data_it[f])		# これは一緒に計算するとちょっと遅くなる。Numpyの一括計算は関数もやってしまうようだ。
		min_intensity = min(data_it[f])
		width_intensity = max_intensity - min_intensity
		signal_rt = np.array(data_rt[f][0:show_signals], dtype = np.float32) / maxrt * field - field_size
		signal_mz = np.array(data_mz[f][0:show_signals], dtype = np.float32) / maxmz * field - field_size
		signal_it = (np.array(data_it[f][0:show_signals], dtype = np.float32) - min_intensity)/ width_intensity * skyheight
		signal_zero = np.zeros_like(signal_rt)	# 地面にあたるZ座標なので全部ゼロ。
		
		# 視点(xyz)-終点(xyz)に並べ、行列入れ替え、平坦化、globalのnp配列に送る
		signal_cube = np.stack([signal_rt,signal_mz,signal_zero,signal_rt,signal_mz,signal_it], 0)	# 二次元配列にする。0はnp.stackの引数
		signal_cube_T = signal_cube.T				# 行列入れ替え
		signal_cube_ravel = signal_cube_T.ravel()	# 平坦化
		signal_vertex.append(signal_cube_ravel)
		
	end = time.time()
	print('set_signal (sec):',end-start)
	glutPostRedisplay()



#####
#	GUI
#####

angle = 0.0		# カーソルの向き
cx= 0.0			# カーソルの位置。ユーザー入力で変える
cy= 0.0
dist= 1.0	# 距離の単位。定数？要らない？
zoom= 3.0					# ズーム。ユーザー入力で変える
rotate_vertical=0.4			# 仰角。ユーザー入力で変える
rotate_horizontal=math.pi	# 回転。ユーザー入力で変える

rotate_vertical_limit_sky = 0.001
rotate_vertical_limit_ground = 0.001

# ピーク選択
library_rt_start = []	# library_rt_start[peak]で。ライブラリ枠の四隅の座標。
library_rt_end = []
library_mz_start = []
library_mz_end = []
library_draw_rt = []		# 各ピークのピークトップの座標とシグナル強度
library_draw_mz = []
library_draw_it = []
library_ave_mz = []
library_label = []		# ラベル
library_top_rt = []		# library_top_rt[peak][file] = Rt。calibrationで使う用
library_top_mz = []
library_top_it = []
library_signalindex = []	# library_signalindex[peak][file][num] = sign の引数
library_cflag = []
library_peaks = 0

def peak_select():
	global library_rt_start
	global library_rt_end
	global library_mz_start
	global library_mz_end
	global library_draw_rt
	global library_draw_mz
	global library_draw_it
	global library_ave_mz
	global library_label
	global library_signalindex
	global library_cflag
	global library_peaks
	
	time_start = time.time()
	
	# カーソル位置とカーソル半径をLCMSのrt/mz軸に変換
	selected_rt = (cx + field_size) / field * maxrt
	selected_mz = (cy + field_size) / field * maxmz
	selected_range = zoom / cursor_size	/ field		# 半径はズーム値で違う。カーソルが円なので。
	selected_range_rt = selected_range * maxrt
	selected_range_mz = selected_range * maxmz
	
	# ユーザーが選択しようとしているシグナルがどれか探す。
	maxsign_it=(-1.0)
	maxsign_rt=(-1.0)
	maxsign_mz=(-1.0)
	maxsign_file = (-1)
	for f in show_file:		# シグナルの中から一番高く見えているものを探して起点にする。カーソルの範囲内。
		max_intensity = data_it[f][0]
		min_intensity = data_it[f][-1]
		width_intensity = max_intensity - min_intensity
		for sign in range(0, show_signals):		# show_signals は定数。真四角にしたから全ファイル同じ値。見えてないデータも対象にするときはrange(0,data_signs[f]):
			if(abs(data_rt[f][sign] - selected_rt) < selected_range_rt):	# 計算が遅いので簡単な計算でクッションする
				if(abs(data_mz[f][sign] - selected_mz) < selected_range_mz):
					d = ((data_rt[f][sign] - selected_rt)/maxrt) **2 + ((data_mz[f][sign] - selected_mz)/maxmz)**2	# maxで割るのはカーソルが円形だから。
					if(d < selected_range**2):
						if(maxsign_it < (data_it[f][sign]-min_intensity)/width_intensity):	# maxで割る。thermoとwatersを比べるためにファイル毎の最大値で割る。
							maxsign_file = f	# 処理が重たいようなら見つけたファイルの中で探すようにするため
							maxsign_rt = data_rt[f][sign]
							maxsign_mz = data_mz[f][sign]
							maxsign_it = (data_it[f][sign]-min_intensity)/width_intensity
						break	# シグナル強い順にソートされているので最初の一個でOK。表示zが最大値maxなので。
	if(maxsign_file == (-1)):	# 範囲内にシグナルが無い場合はキャンセル。
		print('no signal in cursor')
		return(1)
	
	# ピークトップを探す。ユーザーが選んだシグナルの近所で一番強いシグナル。
	search_rt_left = 0.04		# ピークトップの探索範囲。左右で違う・・と思ったら同じでちょうどよかった
	search_rt_right = 0.04
	search_rt_width = (search_rt_left + search_rt_right)/2
	search_rt_shift = (search_rt_right - search_rt_width)
	search_mz_width = 1.0
	peaktop_it = (-1)
	peaktop_rt = (-1)
	peaktop_mz = (-1)
	for f in show_file:		# 表示されているデータの中から。
		max_intensity = data_it[f][0]
		min_intensity = data_it[f][-1]
		width_intensity = max_intensity - min_intensity
		for sign in range(0, show_signals):
			if(abs(data_rt[f][sign] - (maxsign_rt + search_rt_shift)) < search_rt_width):
				if(abs(data_mz[f][sign] - maxsign_mz) < search_mz_width/2):
					if(peaktop_it < (data_it[f][sign]-min_intensity)/width_intensity):	# maxで割る。
						peaktop_rt = data_rt[f][sign]
						peaktop_mz = data_mz[f][sign]
						peaktop_it = (data_it[f][sign]-min_intensity)/width_intensity
						break	# すでにソートされているので最初に見つけたいっこがピークトップ。breakしてOK
	
	# 見つけたピークトップが既存のライブラリ枠に入ってないかチェック
	hitcheck_flag = 0
	for i in range(0,library_peaks):
		librt_w = (library_rt_end[i] - library_rt_start[i])/2	# rt軸上の距離。中心からの距離なので半分
		librt_c = (library_rt_end[i] + library_rt_start[i])/2	# rt軸上の中心の位置
		if(abs(peaktop_rt - librt_c) < librt_w):
			libmz_w = (library_mz_end[i] - library_mz_start[i])/2	# mz軸上の距離。中心からの距離なので半分
			libmz_c = (library_mz_end[i] + library_mz_start[i])/2	# mz軸上の中心の位置
			if(abs(peaktop_mz - libmz_c) < libmz_w):
				hitcheck_flag = 1
				break
	if(hitcheck_flag == 1):
		if(selected_rt > peaktop_rt):print('selected already: right')
		if(selected_rt < peaktop_rt):print('selected already: left')
		return(0)		# 被ってたらキャンセルする
	
	# ピークの幅を仮に決める。プリセット範囲内でピークトップから一番遠いところを取る。
	rt_start = peaktop_rt - 0.10		# 仮枠。Rtの幅。左右で違う。左 0.1 右 0.16
	rt_end   = peaktop_rt + 0.26
	search_mz_width = 0.8				# 仮枠。m/zの幅。上下で同じ。
	mz_start = peaktop_mz - search_mz_width/2
	mz_end   = peaktop_mz + search_mz_width/2
	it_limit = 0.01					# ピーク認識のリミット。輝度でトップの何%までとするか。0.01で1%。0.03くらい
	it_limit_early = 0.001
	it_limit_later = 0.001
	index_list_file = []	# ピーク内にあるシグナルのindexリスト。
	index_list_sign = []
	index_early_file = (-1)			# ピークの左と右の端っこのシグナルのindex。[file][sign]
	index_early_sign = (-1)
	index_later_file = (-1)
	index_later_sign = (-1)
	peak_rt_early = peaktop_rt		# ピークの左と右の端っこのRtは抜き出しておく。初期値はピークトップ。
	peak_rt_later = peaktop_rt
	mz_sum = 0						# ピークm/zの平均値。重量平均でなくて全シグナルを等価に扱うほうがいい感じ。
	mz_sum_counter = 0
	for f in show_file:
		max_intensity = data_it[f][0]
		min_intensity = data_it[f][-1]
		width_intensity = max_intensity - min_intensity
		for sign in range(0,show_signals):		# it大きい順にソートされてるので利用する。
			intensity = (data_it[f][sign]-min_intensity)/width_intensity
			if(intensity < peaktop_it * it_limit):	# ピークトップより一定割合低いシグナルを見たらコレ以降対象外のシグナルしかないのでbreak
				break
			target_flag = 0								# Rt, m/z の枠に収まってるかチェック
			if(data_mz[f][sign] > mz_start):
				if(data_mz[f][sign] < mz_end):
					if(data_rt[f][sign] > rt_start):
						if(data_rt[f][sign] < rt_end):
							target_flag = 1
			if(target_flag == 1):						# 対象シグナルを見つけたら番号を収集
				index_list_file.append(f)
				index_list_sign.append(sign)
				if(data_rt[f][sign] < peaktop_rt):	# ピークトップより速いか遅いかで処理が違うので。
					if(peak_rt_early > data_rt[f][sign]):		# 一番遠いものを探す。
						peak_rt_early = data_rt[f][sign]
				else:
					if(peak_rt_later < data_rt[f][sign]):
						peak_rt_later = data_rt[f][sign]
				mz_sum += data_mz[f][sign]			# 枠内のシグナルを積算する。輝度の小さいノイズは外れているのでここでついでに計算するのが高精度だろう。
				mz_sum_counter += 1					# どう見ても見えてるシグナル本数より多い。すごく近いrtmzに複数のシグナルがある模様。
	average_mz = peaktop_mz
	if(mz_sum_counter > 0):		# ピークが持つ m/z は単純な平均値とする。
		average_mz = mz_sum/mz_sum_counter

	rtgap = 0.003					# 同じRtと判定する基準。waters のRt間隔は 0.004、thermoは0.008だったのでそれより小さい値。
	if(abs(peak_rt_later - peak_rt_early) < rtgap):		# scan一回分しかRtの幅がない場合はノイズなのでreturn。
		print('too narrow peak')
		return(1)

	# ギャップがある場合は詰める。ギャップとはシグナルのない時間のこと
	rt_list = []
	for s in range(0, len(index_list_sign)):
		rt_list.append(data_rt[index_list_file[s]][index_list_sign[s]])
	rt_list.sort()
	gap = 0.02	# 判定幅。シグナルのない区間。
	for r in range(0,len(rt_list)-1):
		if(rt_list[r] > peaktop_rt):				# 右側について。
			if(rt_list[r+1]-rt_list[r] > gap):		# 0.02min 以上シグナルの無いところがあったらそこまで詰める
				peak_rt_later = rt_list[r]
				break
	for r in range(len(rt_list)-1, -1,-1):
		if(rt_list[r] < peaktop_rt):				# 左側について。
			if(rt_list[r]-rt_list[r-1] > gap):		# Rtに 0.02min 以上の差があったらそこで止めておく。
				peak_rt_early = rt_list[r]
				break
	
	# 隣のピークにかかっているか調べる
	it_list = []	# まずピーク内シグナルをRtでソートする。
	rt_list = []	# 同じ座標に複数のシグナルがあるようなので、その中の一番高いやつだけ取ってスムージングに使う案
	for s in range(0, len(index_list_sign)):
		rt_list.append(data_rt[index_list_file[s]][index_list_sign[s]])		# ピーク内シグナルのリストができてるので使う
		it_ = (data_it[index_list_file[s]][index_list_sign[s]] - data_it[index_list_file[s]][-1] )/ data_it[index_list_file[s]][0]
		it_list.append(it_)
	rt_array = np.array(rt_list)
	it_array = np.array(it_list)			# argsort を使いたいのでNumpy化
	sorted_rt_array = np.sort(rt_array)		# Rtで小さい順にソートする。
	sorted_index = np.argsort(rt_array)
	sorted_it_array = it_array[sorted_index]
	
	# ピーク内シグナルをrtでソート、一定区間内ごとに最強のシグナルを探す。
	new_rt_list =[]		# 同じRtのシグナル群から最強のものを取り出したリスト
	new_it_list =[]
	rt = sorted_rt_array[0]			# 内部変数初期値。Rtのカウンター。
	max_it = sorted_it_array[0]		# 内部変数初期値。同一Rtで一番高い輝度を持ったシグナルの輝度とRt
	max_rt = sorted_rt_array[0]
	for s in range(1, len(sorted_rt_array)-1):
		if(sorted_rt_array[s] - rt > rtgap):	# Rt値が変わったら次の群に移ったとする
			new_rt_list.append(max_rt)		# 前の群の最強のシグナルを記録
			new_it_list.append(max_it)
			max_rt = sorted_rt_array[s]		# 次の群を調べるための初期値を設定
			max_it = sorted_it_array[s]
			rt = sorted_rt_array[s]
		else:									# 同じ座標のシグナルだったときは同群なので
			if(max_it < sorted_it_array[s]):
				max_it = sorted_it_array[s]		# 前より強い輝度だったらとっとく
				max_rt = sorted_rt_array[s]
	
	# ピーク形状をスムージングして上がり調子の場所を見つけたら詰める
	num = 7				# スムージング幅と判定幅。シグナル数より多いと判定できない。小さすぎると偶然ヒットしてしまう。
	smoose_counter=0	# ピークトップが正しく選択できてない場合は左右どっちかが上がり調子スロープ上なので最初の判定でひっかかる。それを検出するためのカウンター
	for s in range(0, len(new_rt_list)-num-num):	# 右側。ピークトップから右へ見ていく
		if(new_rt_list[s] > peaktop_rt):
			mean = []	# スムージングする
			for i in range(0,num):
				mean.append(sum(new_it_list[s+i:s+i+num])/num)
			judge = 0	# 判定する
			for i in range(0,num-1):
				if(mean[i+1]-mean[i] > 0):judge += 1
			if(judge == num-1):
				if(peak_rt_later > new_rt_list[s]):
					peak_rt_later = new_rt_list[s]
					if(smoose_counter==0):		# 最初の判定で上がり調子だった場合はピークトップの判定が正しくない。
						print('wrong peaktop: right')
						return(1)
				break
			smoose_counter += 1
	smoose_counter=0
	for s in range(len(new_rt_list)-1, num-1, -1):	# 左側。ピークトップから左へ見ていく
		if(new_rt_list[s] < peaktop_rt):
			mean = []	# スムージングする
			for i in range(0,num):
				mean.append(sum(new_it_list[s+i-num:s+i])/num)
			judge = 0	# 判定する
			for i in range(0,num-1):
				if(mean[i+1]-mean[i] < 0):judge += 1
			if(judge == num-1):
				if(peak_rt_early < new_rt_list[s]):
					peak_rt_early = new_rt_list[s]
					if(smoose_counter==0):		# 最初の判定で上がり調子だった場合はピークトップの判定が正しくない。
						print('wrong peaktop:left')
						return(1)
				break
			smoose_counter += 1
	
	# ユーザー指定のライブラリに照合してラベルがあればつけておく。なければブランクのまま
	std_hit = (-1)
	std_mz_width = 0.3	# 許容幅。両側。
	std_rtdist_min = 100	# Rt が一番近いもの
	calibration_flag = (-1)
	for std in range(0,standards):
		if(abs(standard_mz[std] - average_mz) < std_mz_width):			# m/z値が一致するものの中で
			if(std_rtdist_min > abs(standard_rt[std]-peaktop_rt)):
				std_rtdist_min = abs(standard_rt[std]-peaktop_rt)		# ピークトップのRtが一番近いもの。m/zが同じで違う化合物。
				std_hit = std
	peak_label = ''
	if(std_hit >(-1)):
		peak_label = standard_label[std_hit]
	calibration_flag = std_hit		# mzキャリブレーションのフラグ代わりに標品番号を使う
	
	# 屏風用のindexデータを採取。全file対象なので表示ファイルのみ対象のルーチンではついでに計算できなかった。
	hit_index = []			# sign = hit_index[f][num] 。numは0からの通し番号
	for f in range(0,files):
		hit_index.append([])
		array_rt = np.array(data_rt[f][0:show_signals], dtype = np.float32)
		array_mz = np.array(data_mz[f][0:show_signals], dtype = np.float32)
		array_it = np.array(data_it[f][0:show_signals], dtype = np.float32)
		sorted_array_rt = np.sort(array_rt)		# Rt でソートする。
		index_array = np.argsort(array_rt)		# sign = index_array[i] のはず。
		sorted_array_mz = array_mz[index_array]
		sorted_array_it = array_it[index_array]
		
		start = 0	# Rt でソートしたので開始点まで飛ばせる
		start_flag = 0
		for i in range(0,show_signals,100):		# 枠に入りそうなところまで飛ばす。100刻みで飛ばす
			if(sorted_array_rt[i] > peak_rt_early - rtgap ):
				start = i-100					# 100刻みだと通り過ぎるから戻す。
				if(start < 0): start = 0		# 最初の100で枠に入ってた場合
				break
		for i in range(start,show_signals):		# さらに1刻みで飛ばしてスタート地点まで行く
			if(sorted_array_rt[i] > peak_rt_early - rtgap):
				if(abs(sorted_array_mz[i] - average_mz) < search_mz_width/2):	# 枠に入ったら
					start = i
					break
			if(sorted_array_rt[i] > peak_rt_later + rtgap):		# 通り過ぎちゃったらデータ内に該当シグナルなし
				start = i		# ピーク右端をスタートにする
				break
		if(sorted_array_rt[start] < peak_rt_later + rtgap):
			prev_rt = sorted_array_rt[start]		# スタート地点を初期値とする
			topsignal_index = index_array[start]
			topsignal = data_it[f][topsignal_index]
			for i in range(start, show_signals):	# ソートしただけなので最大はshow_signalsのはず
				if(abs(sorted_array_mz[i] - average_mz) < search_mz_width/2):	# 枠に入ったら
					if(prev_rt + rtgap < sorted_array_rt[i]):	# 次のScanかどうか判定。rtが+rtgap分以上ずれたら次のscan。
						hit_index[f].append(topsignal_index)	# 前のScanでみつけたやつを登録
						prev_rt = sorted_array_rt[i]
						topsignal_index = index_array[i]
						topsignal = data_it[f][topsignal_index]
					else:
						if(topsignal < data_it[f][index_array[i]]):
							topsignal_index = index_array[i]
							topsignal = data_it[f][topsignal_index]
				if(sorted_array_rt[i] > peak_rt_later + rtgap):	# 通り過ぎたらおわり
					hit_index[f].append(topsignal_index)	# 最後のScanでみつけたやつはここで登録
					break
	
	# データを採取。Rtのキャリブレーション用
	library_top_rt.append([])		# library_top_rt[peak][file] でそのファイル内のピークトップ
	library_top_mz.append([])
	library_top_it.append([])
	for f in range(0,files):					# 全ファイル対象。
		flag = 0
		for sign in range(0,show_signals):		# 見えているシグナル限定。リミットを動的にするならdata_signs[f]で全シグナル検索しとくか？
			if(data_rt[f][sign] > peak_rt_early):		# 枠に入ってるか調べる
				if(data_rt[f][sign] < peak_rt_later):
					if(abs(data_mz[f][sign] - average_mz) < search_mz_width/2):
						flag = 1
			if(flag == 1):								# 枠に入ってた最初の１個が一番高いシグナル
				library_top_rt[library_peaks].append(data_rt[f][sign])
				library_top_mz[library_peaks].append(data_mz[f][sign])
				top_it = (data_it[f][sign]-min_intensity)/width_intensity
				library_top_it[library_peaks].append(top_it)	# itはどうしようかな。ファイル内だからそのままでいいか？
				break
		if(flag == 0):	# 枠内にシグナルがなかったときはダミーデータを入れておく。
			library_top_rt[library_peaks].append(0)
			library_top_mz[library_peaks].append(0)
			library_top_it[library_peaks].append(0)
	
	# 完成。ライブラリ枠とラベルを描くための配列に登録。
	library_rt_start.append(peak_rt_early)		# 枠
	library_rt_end.append(peak_rt_later)
	library_mz_start.append(average_mz - search_mz_width/2)
	library_mz_end.append(average_mz + search_mz_width/2)
	library_draw_rt.append(peaktop_rt)			# ラベル
	library_draw_mz.append(peaktop_mz)
	library_draw_it.append(peaktop_it)		# peaktop_it は/maxで割った値。注意。
	library_ave_mz.append(average_mz)
	library_label.append(peak_label)
	library_signalindex.append(hit_index)
	library_cflag.append(calibration_flag)
	library_peaks += 1
	
	time_mid = time.time()
	
	set_library()	# VBO表示用のNumpyを用意する。
	
	print('setlibvertex', time.time() - time_mid, 'selectpeak', time_mid - time_start)
	return(0)
	


# 高いピークを選んで自動でピークセレクトする。
autoselect_resume = 0
autoselect_setting = 0
def peak_select_auto():
	global autoselect_resume
	global autoselect_setting
	global cursor_size
	global zoom
	global cx	# 動いているのが見えるようにする。
	global cy
	cursor_bkup = cursor_size
	cx_bkup = cx	# バックアップする。
	cy_bkup = cy
	
	start = time.time()
	num = show_signals
	if(num < show_signals_underlimit):
		num = show_signals_underlimit
	
	if(autoselect_setting != num*len(show_file)):	# ファイルが追加されたりしたときの処理
		autoselect_resume = 0
		autoselect_setting = num*len(show_file)
	
	# 表示シグナルをひとつの一次元配列にしてソート。
	it_list = []
	rt_list = []
	mz_list = []
	for f in show_file:
		min_intensity = data_it[f][-1]
		max_intensity = data_it[f][0]
		width_intensity = max_intensity - min_intensity
		it = (np.array(data_it[f][:num], dtype = np.float32) - min_intensity) / width_intensity
		it_list += it.tolist()			# なぜかnumpy ndarrayのままだと連結できないので無理矢理。。
		rt_list += data_rt[f][:num]
		mz_list += data_mz[f][:num]
	it_array = np.array(it_list,dtype = np.float32)
	rt_array = np.array(rt_list,dtype = np.float32)
	mz_array = np.array(mz_list,dtype = np.float32)
	sorted_it_array = np.sort(it_array)[::-1]
	sorted_index = np.argsort(it_array)[::-1]
	sorted_rt_array = rt_array[sorted_index]
	sorted_mz_array = mz_array[sorted_index]
	
	# 強い順に並んだので、順番にpeak_select関数に投げてみる。
	cursor_size = 1000*zoom		# これならzoom値を変更せずにちょうどいいcursorサイズにできる
	errors = 0
	peaks = 0	# 今回見つけたピークの数を数える
	for i in range(autoselect_resume,autoselect_setting):
		flag = 1		# 既存ライブラリの中のシグナルでないかどうか調べる。ちょっと範囲広げた方がいいかな？
		for p in range(0,library_peaks):
			if(sorted_rt_array[i] > library_rt_start[p]):
				if(sorted_rt_array[i] < library_rt_end[p]):
					if(sorted_mz_array[i] > library_mz_start[p]):
						if(sorted_mz_array[i] < library_mz_end[p]):
							flag = 0
							break
		if(flag == 1):	#
			cx = sorted_rt_array[i] / maxrt * field - field_size
			cy = sorted_mz_array[i] / maxmz * field - field_size
			before = library_peaks
			cursor_size = 1000*zoom		# 直前で計算する。ユーザーの操作の影響を最小限にするため。
			errors += peak_select()
			if(library_peaks > before):
				peaks += 1
				autoselect_resume = i
				draw()
			break_flag = 0
			if(peaks > 30):break_flag = 1		# 30個くらいから重たくなる。
			if(errors > 10):break_flag = 2
			if(break_flag > 0):
				print(break_flag, end=' ')
				autoselect_resume = i
				break
	
	print('auto_peakselect tested:',library_peaks, 'peaks,', autoselect_resume, '/', autoselect_setting, 'signals tested', int((time.time()-start)*10)/10, 'sec')
	
	cx = cx_bkup	# いじくり回したグローバル変数をもとに戻す。
	cy = cy_bkup
	cursor_size = cursor_bkup
	
# ピーク選択を解除
def peak_delete():
	
	global library_rt_start
	global library_rt_end
	global library_mz_start
	global library_mz_end
	global library_draw_rt
	global library_draw_mz
	global library_draw_it
	global library_ave_mz
	global library_label
	global library_top_rt
	global library_top_mz
	global library_top_it
	global library_peaks
	global library_signalindex
	global library_cflag
	
	# カーソル位置とカーソル半径をLCMSのrt/mz軸に変換
	selected_rt = (cx + field_size) / field * maxrt
	selected_mz = (cy + field_size) / field * maxmz
	selected_range = zoom / cursor_size / field		# 範囲はズーム値で違う。カーソルが円なので
	
	# 四角形と円の当たり判定
	hit = []	# 当たったライブラリのindexを全部とっとく。
	hits = 0
	for i in range(0,library_peaks):
		lib_rt = selected_rt		# 四角形の中で円の中心に一番近い点を探す
		lib_mz = selected_mz
		if(library_rt_start[i] > selected_rt):
			lib_rt = library_rt_start[i]
		if(library_rt_end[i] < selected_rt):
			lib_rt = library_rt_end[i]
		if(library_mz_start[i] > selected_mz):
			lib_mz = library_mz_start[i]
		if(library_mz_end[i] < selected_mz):
			lib_mz = library_mz_end[i]
		dist_x = abs(selected_rt - lib_rt) / maxrt		# 四角形内で一番近い点から円の中心へのベクトル
		dist_y = abs(selected_mz - lib_mz) / maxmz
		if(dist_x**2 + dist_y**2 < selected_range **2):
			hit.append(i)	# ヒットしたライブラリを全部登録する
			hits += 1
	
	for i in range(hits-1, -1, -1):		# ヒットしたやつを後ろから順に消していく。
		library_rt_start.pop(hit[i])
		library_rt_end.pop(hit[i])
		library_mz_start.pop(hit[i])
		library_mz_end.pop(hit[i])
		library_draw_rt.pop(hit[i])
		library_draw_mz.pop(hit[i])
		library_draw_it.pop(hit[i])
		library_ave_mz.pop(hit[i])
		library_label.pop(hit[i])
		library_top_rt.pop(hit[i])
		library_top_mz.pop(hit[i])
		library_top_it.pop(hit[i])
		library_signalindex.pop(hit[i])
		library_cflag.pop(hit[i])
		library_peaks -= 1
	
	if(hits>0):set_library()

# ライブラリ登録をリセット
def peak_delete_all():
	global library_rt_start
	global library_rt_end
	global library_mz_start
	global library_mz_end
	global library_draw_rt
	global library_draw_mz
	global library_draw_it
	global library_ave_mz
	global library_label
	global library_top_rt
	global library_top_mz
	global library_top_it
	global library_signalindex
	global library_cflag
	global library_peaks
	library_rt_start.clear()
	library_rt_end.clear()
	library_mz_start.clear()
	library_mz_end.clear()
	library_draw_rt.clear()
	library_draw_mz.clear()
	library_draw_it.clear()
	library_ave_mz.clear()
	library_label.clear()
	library_top_rt.clear()
	library_top_mz.clear()
	library_top_it.clear()
	library_signalindex.clear()
	library_cflag.clear()
	library_peaks = 0
	set_library()
	
# m/z のキャリブレーション
def calibration_mz():
	global data_mz		# 何故か書かなくても機能する不思議
	
	for f in range(0,files):
		# まず選択ピークのm/z値と理想値のリスト
		measured_mz = []			# このペアを作っていく
		ideal_mz = []
		effective_peaks = 0
		for p in range(0, library_peaks):
			if(library_cflag[p] > (-1)):		# 標品番号がフラグ扱い
				#	ピークに含まれるシグナルのm/z値の平均を取る。実測値とする。
				if(len(library_signalindex[p][f])>5):	# ピーク内のシグナル数
					sum_mz = 0
					for n in range(0, len(library_signalindex[p][f]) ):
						sum_mz += data_mz[f][ library_signalindex[p][f][n] ]
					if(len(library_signalindex[p][f])>0):
						measured_mz.append( sum_mz / len(library_signalindex[p][f]) )	# m/z実測値 = ピーク内平均
						ideal_mz.append( standard_mz[library_cflag[p]] )	# m/z 理想値（標品のm/z）= ユーザー入力値
						effective_peaks += 1
		# 実測値を理想値に変換するための１次関数を生成する
		slope = 0		# 傾き。y=ax+bのa。補正なしの場合は1だが、初期値は0。この変数で積算してnで割るまでやるので。
		counter = 0
		for n in range( 0, effective_peaks ):
			for m in range(n+1, effective_peaks ):
				y = ideal_mz[m] - ideal_mz[n]
				x = measured_mz[m] - measured_mz[n]
				if(abs(x) > 10):
					if(abs(y) > 10):	# 実測値か理想値が近すぎるペアを使うのはノイズの影響が大きく出るので外す。
						slope += y/x
						counter += 1
		if(counter > 0):
			slope = slope / counter
		else:
			slope = 1				# 補正値にできる値の設定が無いファイルのときは傾きは1。
		
		intercept = 0	#	Y切片。y=ax+b
		counter_i = 0
		for n in range( 0, len(measured_mz) ):
			intercept += ideal_mz[n] - slope * measured_mz[n]
			counter_i += 1
		if(counter_i>0):
			intercept = intercept / counter_i
		
		print('calib_mz file: ',f, 'slope:', slope, 'intercept:', intercept, 'effective_peaks:', effective_peaks)
		
		# 実測値に補正を入れてみる。この計算は時間かかる注意
		if(counter + counter_i > 0):
			data_mz[f] = (np.array(data_mz[f], dtype=np.float32) * slope + intercept).tolist()
		
	set_signal()
	set_library()
	

# Rtをキャリブレーション。ピークトップを合わせに行く。
def calibration_rt():
	global data_rt
	
	# まず合わせに行くべき理想のRt値を決める。
	ideal_rt = []		# 目標値とするRt。ピークごとにあるので引数はpeak番号
	measured_rt = []	# 実測値のRt。引数は[peak][file]
	for p in range(0, library_peaks):
		peaktop_rt_average = 0
		counter = 0
		measured_rt.append([])
		for f in range(0, files):
			peaktop = 0
			peaktop_rt = (-1)
			if(len(library_signalindex[p][f]) > 5):
				for n in range(0, len(library_signalindex[p][f]) ):
					if(peaktop < data_it[f][ library_signalindex[p][f][n] ] ):
						peaktop = data_it[f][ library_signalindex[p][f][n] ]
						peaktop_rt = data_rt[f][ library_signalindex[p][f][n] ]
				if(peaktop_rt > 0):
					peaktop_rt_average += peaktop_rt
					counter += 1	# ピークの会ったファイルの数をカウントする
			measured_rt[p].append(peaktop_rt)	# 実測値。そのピークがないファイルでも登録する。(-1)が入る。
		if(counter > 0):	# ゼロなことはないけど将来的にありえるから
			peaktop_rt_average = peaktop_rt_average / counter
		ideal_rt.append(peaktop_rt_average)
	
	# slope を計算する
	for f in range(0, files):
		slope = 0
		counter = 0
		for n in range(0, library_peaks):
			if(measured_rt[n][f] > 0):		# ピークが無い場合は(-1)が入っている
				for m in range(n+1, library_peaks):
					if(measured_rt[m][f] > 0):		# ピークが無い場合は(-1)が入っている
						y = ideal_rt[m] - ideal_rt[n]
						x = measured_rt[m][f] - measured_rt[n][f]
						if(abs(x) > 1):
							if(abs(y) > 1):	# 実測値か理想値が近すぎるペアを使うのはノイズの影響が大きく出るので外す。
								slope += y/x
								counter += 1
		if(counter > 0):
			slope = slope / counter
		else:
			slope = 1				# 補正値しない場合の傾きは1。
		
		intercept = 0	#	Y切片。y=ax+b
		counter_i = 0
		for n in range( 0, library_peaks ):
			if(measured_rt[n][f] > 0):	# ピークが無い場合は(-1)が入っている
				intercept += ideal_rt[n] - slope * measured_rt[n][f]
				counter_i += 1
		if(counter_i>0):
			intercept = intercept / counter_i
		
		print('calib_rt: file#: ',f, 'slope:', slope, 'intercept:', intercept)
		
		# 実測値に補正を入れてみる。この計算は時間かかる注意
		if(counter + counter_i > 0):
			data_rt[f] = (np.array(data_rt[f], dtype=np.float32) * slope + intercept).tolist()
	set_signal()
	set_library()


# 大きなRtの差を補正する。２ペアを使って1次関数にする。
def calibration_rt_large():
	
	global data_rt
	
	# ２ペアを作れるかどうかチェック。ついでにペアになるピークの番号をメモる
	two_pair_flag = 0	# ２ペアができた判定フラグ
	peaknum_pair1 = 0			# ピークゼロ番とペアになるやつの番号。ピーク４つで０番以外なので１２３のどれか
	peaknum_pair2 = []			# もうひとつのペア。１２３のうちふたつなので配列。
	if(library_peaks == 4):
		for p in range(1,library_peaks):
			if(abs(library_ave_mz[p] - library_ave_mz[0]) < 0.3):
				peaknum_pair1 = p
				break
		if(peaknum_pair1 == 0):return(0)
		for p in range(1,library_peaks):	# １２３番のうち０番とペア(pair1)でないもの同士
			if(peaknum_pair1 != p):
				peaknum_pair2.append(p)
		if(abs(library_ave_mz[peaknum_pair2[0]] - library_ave_mz[peaknum_pair2[1]]) < 0.3):
			two_pair_flag = 1
	print('1', two_pair_flag)
	# ２ペアを作れた場合は補正できるファイルがあるか調べる
	filenum_target_pair0 = []	# ファイル数が少ない方のファイルリスト
	peaknum_target_pair0 = 0	# ファイル数が少ない方のピーク番号。０番か１〜３のどれか
	filenum_standard_pair0 = []		# ファイル数が多い方。こっちは動かさない。
	peaknum_standard_pair0 = 0
	filenum_target_pair1 = []	# ファイル数が少ない方のファイルリスト
	peaknum_target_pair1 = 0	# ファイル数が少ない方のピーク番号。０番か１〜３のどれか
	filenum_standard_pair1 = []		# ファイル数が多い方。こっちは動かさない。
	peaknum_standard_pair1 = 0
	if(two_pair_flag == 1):
		# まずペア１について
		file_pair1_0 = []	# ０番ピークを持つファイルのリスト
		file_pair1_p = []	# ０番の対になるピークを持つファイルのリスト
		for f in range(0,files):	# まずどっちに属する方が多いか調べる
			if(len(library_signalindex[0][f]) > 5):		file_pair1_0.append(f)
			if(len(library_signalindex[peaknum_pair1][f]) > 5):	file_pair1_p.append(f)
		if(len(file_pair1_0) >0 and len(file_pair1_p)>0):
			if(len(file_pair1_0) <= len(file_pair1_p)):		# 少ない方を補正対象とする
				filenum_target_pair0 = file_pair1_0
				filenum_standard_pair0 = file_pair1_p
				peaknum_target_pair0 = 0
				peaknum_standard_pair0 = peaknum_pair1
			else:
				filenum_target_pair0 = file_pair1_p
				filenum_standard_pair0 = file_pair1_0
				peaknum_target_pair0 = peaknum_pair1
				peaknum_standard_pair0 = 0
			two_pair_flag += 1
		# 次にペア２について
		file_pair2_1 = []
		file_pair2_2 = []
		for f in range(0,files):
			if(len(library_signalindex[ peaknum_pair2[0] ][f]) > 5):	file_pair2_1.append(f)
			if(len(library_signalindex[ peaknum_pair2[1] ][f]) > 5):	file_pair2_2.append(f)
		if(len(file_pair2_1) >0 and len(file_pair2_2)>0):		# 両方にピークがある場合。少ない方を補正対象とする
			if(len(file_pair2_1) <= len(file_pair2_2)):
				filenum_target_pair1 = file_pair2_1
				filenum_standard_pair1 = file_pair2_2
				peaknum_target_pair1 = peaknum_pair2[0]
				peaknum_standard_pair1 = peaknum_pair2[1]
			else:
				filenum_target_pair1 = file_pair2_2
				filenum_standard_pair1 = file_pair2_1
				peaknum_target_pair1 = peaknum_pair2[1]
				peaknum_standard_pair1 = peaknum_pair2[0]
			two_pair_flag += 1
	print('3', two_pair_flag)
	print('pair1 peaknum:', peaknum_target_pair0, peaknum_standard_pair0)
	print('pair2 peaknum:', peaknum_target_pair1, peaknum_standard_pair1)
	print('pair1target filenum:', filenum_target_pair0)
	print('pair2target filenum:', filenum_target_pair1)
	print('pair1standard filenum:', filenum_standard_pair0)
	print('pair2standard filenum:', filenum_standard_pair1)
	# 両方のピークペアで補正対象と判定されたファイルを選ぶ
	filenum_target = []
	if(two_pair_flag == 3):			# ２ペアがきちんとできて、４つともカラピークじゃない状態
		for i in filenum_target_pair0:
			for j in filenum_target_pair1:
				if(i == j):
					filenum_target.append(i)		# 補正対象リスト２つで重複しているファイルを補正対象
	
	print(filenum_target)
	# 補正先のrtを計算する
	rt_standard_pair0 = 0
	rt_standard_pair1 = 0
	if(len(filenum_target)>0):	# 補正対象ファイルが１個以上みつかった場合
		# まずペア１の補正先を計算
		counter = 0				# 各ファイルにおけるピークトップのRtを探して平均する
		average_rt = 0
		for f in filenum_standard_pair0:
			maximum_it = 0
			maximum_rt = 0
			for n in range(0, len(library_signalindex[peaknum_standard_pair0][f]) ):
				if( maximum_it < data_it[f][library_signalindex[peaknum_standard_pair0][f][n]] ):
					maximum_it = data_it[f][library_signalindex[peaknum_standard_pair0][f][n]]
					maximum_rt = data_rt[f][library_signalindex[peaknum_standard_pair0][f][n]]
			average_rt += maximum_rt
			counter += 1
		rt_standard_pair0 = average_rt/counter
		# 次にペア２の補正先を計算
		counter = 0				# 各ファイルにおけるピークトップのRtを探して平均する
		average_rt = 0
		for f in filenum_standard_pair1:
			maximum_it = 0
			maximum_rt = 0
			for n in range(0, len(library_signalindex[peaknum_standard_pair1][f]) ):
				if( maximum_it < data_it[f][library_signalindex[peaknum_standard_pair1][f][n]] ):
					maximum_it = data_it[f][library_signalindex[peaknum_standard_pair1][f][n]]
					maximum_rt = data_rt[f][library_signalindex[peaknum_standard_pair1][f][n]]
			average_rt += maximum_rt
			counter += 1
		rt_standard_pair1 = average_rt/counter
	print('rt_standard_pair1/2', rt_standard_pair1, rt_standard_pair0)
	
	# slopeとinterceptを計算。補正距離が近すぎる場合は補正しない
	if(abs(rt_standard_pair1 - rt_standard_pair0) > 1.0):	
		for f in filenum_target:
			maximum_it = 0
			rt_target_pair0 = 0		# ピークトップを探す。
			for n in range(0, len(library_signalindex[peaknum_target_pair0][f]) ):
				if( maximum_it < data_it[f][library_signalindex[peaknum_target_pair0][f][n]] ):
					maximum_it = data_it[f][library_signalindex[peaknum_target_pair0][f][n]]
					rt_target_pair0 = data_rt[f][library_signalindex[peaknum_target_pair0][f][n]]
			maximum_it = 0
			rt_target_pair1 = 0		# ピークトップを探す
			for n in range(0, len(library_signalindex[peaknum_target_pair1][f]) ):
				if( maximum_it < data_it[f][library_signalindex[peaknum_target_pair1][f][n]] ):
					maximum_it = data_it[f][library_signalindex[peaknum_target_pair1][f][n]]
					rt_target_pair1 = data_rt[f][library_signalindex[peaknum_target_pair1][f][n]]
			print(rt_target_pair1, rt_target_pair0)
			if(abs(rt_target_pair1 - rt_target_pair0) > 1.0):
				slope = (rt_standard_pair1 - rt_standard_pair0) / (rt_target_pair1 - rt_target_pair0)
				intercept = rt_standard_pair0 - slope * rt_target_pair0
				print(f, slope, intercept)
				data_rt[f] = (np.array(data_rt[f], dtype=np.float32) * slope + intercept).tolist()
	set_signal()
	peak_delete_all()
	set_library()

# キャリブレーションによる補正を元に戻す
def calibration_reset_rt():
	start = time.time()
	global data_rt
#	global data_mz
	data_rt.clear()
#	data_mz.clear()
	for f in range(0,files):	# copyモジュールのdeepcopy関数が異様に遅い。appendでも参照渡しになってないように見える不思議
		data_rt.append(data_rt_bkup[f])
#		data_mz.append(data_mz_bkup[f])
	set_signal()
	set_library()
	print(time.time() - start)

def calibration_reset_mz():
	start = time.time()
#	global data_rt
	global data_mz
#	data_rt.clear()
	data_mz.clear()
	for f in range(0,files):	# copyモジュールのdeepcopy関数が異様に遅い。appendでも参照渡しになってないように見える不思議
#		data_rt.append(data_rt_bkup[f])
		data_mz.append(data_mz_bkup[f])
	set_signal()
	set_library()
	print(time.time() - start)

# ピーク積分値をファイルに書き出し
def export_data():
	outfile = project + '_export.txt'
	savemode = 'x'
	if os.path.isfile(outfile):savemode = 'w'
	filehandle = open(outfile, savemode)
	for f in range(0,files):
		strings = '\t'+filename[f]
		filehandle.write(strings)
	filehandle.write('\n')
	
	refresh_librarysignalindex()	# calibrationとかでズレてることがあるので更新する。
	for p in range(0,library_peaks):
		label = str(library_label[p]) + ' m/z=' + str(int(library_ave_mz[p]*1000)/1000) + ' Rt=' + str(int(library_draw_rt[p]*10)/10)
		filehandle.write(label)
		peakvolume = 0
		for f in range(0, files):
			for n in range(0, len(library_signalindex[p][f])):
				peakvolume += data_it[f][library_signalindex[p][f][n]]
			strings = '\t' + str(peakvolume)
			peakvolume = 0
			filehandle.write(strings)
		filehandle.write('\n')
	filehandle.close()

# ライブラリ枠と屏風を画面に表示するためのVBOを作る。
library_vertex = []		# 屏風のVBOはファイルごと。 library_vertex[file]
library_square_vertex = np.zeros(6*library_peaks, dtype = np.float32)	# ライブラリの枠をvboで表示するためのNumpy array
def set_library():
	global library_square_vertex
	global library_vertex
	global library_ave_mz
	
	# ライブラリ枠
	setlist = []
	for p in range(0,library_peaks):
		rt1 = library_rt_start[p] / maxrt * field - field_size
		mz1 = library_mz_start[p] / maxmz * field - field_size
		rt2 = library_rt_end[p] / maxrt * field - field_size
		mz2 = library_mz_end[p] / maxmz * field - field_size
		it = 0		# 水色の枠は高さ = 0.001 * skyheight とかにして浮かせてたけどやめたほうがよさそうなのでやめとく。
		setlist += [rt1, mz1, it, rt1, mz2, it, 
					rt1, mz2, it, rt2, mz2, it, 
					rt2, mz2, it, rt2, mz1, it, 
					rt2, mz1, it, rt1, mz1, it ]
	library_square_vertex = np.array(setlist, dtype = np.float32)
	
	# ライブラリ屏風。どうしようかな。
	library_vertex.clear()		# ピークを単品追加のときは追加にすると速いが・・
	for f in range(0,files):
		max_intensity = max(data_it[f])		# これは一緒に計算するとちょっと遅くなる。Numpyの一括計算は関数もやってしまうようだ。
		min_intensity = min(data_it[f])
		width_intensity = max_intensity - min_intensity
		byobu_lines_list = []
		for p in range(0,library_peaks):
			if(len(library_signalindex[p][f])-1 > 0):
				for n in range(0,len(library_signalindex[p][f])-1):
					rt1 = data_rt[f][library_signalindex[p][f][n]]   / maxrt * field - field_size
					rt2 = data_rt[f][library_signalindex[p][f][n+1]] / maxrt * field - field_size
					mz1 = data_mz[f][library_signalindex[p][f][n]]   / maxmz * field - field_size
					mz2 = data_mz[f][library_signalindex[p][f][n+1]] / maxmz * field - field_size
					it1 = (data_it[f][library_signalindex[p][f][n]]   - min_intensity)/ width_intensity * skyheight
					it2 = (data_it[f][library_signalindex[p][f][n+1]] - min_intensity)/ width_intensity * skyheight
					byobu_lines_list += [rt1, mz1, it1, rt2, mz2, it2]
		byobu_vertex = np.array(byobu_lines_list, dtype = np.float32)			# ライブラリ屏風をvboで表示するためのNumpy array
		library_vertex.append(byobu_vertex)
#		library_vertex.append(byobu_lines_list)
	
	# ライブラリのラベル用平均m/zを再計算。別の関数にまとめたほうがいいけどとりあえずここに書いとく
	library_ave_mz.clear()
	for p in range(0,library_peaks):
		avemz = 0
		counter = 0
		for f in range(0,files):
			for n in range(0,len(library_signalindex[p][f])):
				avemz += data_mz[f][ library_signalindex[p][f][n] ]
				counter += 1
		if(counter > 0):
			avemz = avemz/counter
		library_ave_mz.append(avemz)
	glutPostRedisplay()

# 屏風用のindexデータを更新する。
def refresh_librarysignalindex():
	global library_signalindex
	library_signalindex.clear()		# library_signalindex[peak][file][num]
	for p in range(0,library_peaks):
		library_signalindex.append([])
		for f in range(0,files):
			library_signalindex[p].append([])	# 初期化。[p][f][n]なのでループの中ではできない
	rtgap = 0.003				# 同じRtと認識する時間幅
	search_mz_width = 0.8		# mzの幅

	for f in range(0,files):
		array_rt = np.array(data_rt[f][0:show_signals], dtype = np.float32)
		array_mz = np.array(data_mz[f][0:show_signals], dtype = np.float32)
		array_it = np.array(data_it[f][0:show_signals], dtype = np.float32)
		sorted_array_rt = np.sort(array_rt)		# Rt でソートする。
		index_array = np.argsort(array_rt)		# sign = index_array[i] のはず。
		sorted_array_mz = array_mz[index_array]	# 通し番号iに対してシグナル番号はindex_array[i]
		sorted_array_it = array_it[index_array]
		
		for p in range(0,library_peaks):
			hit_index = []	# hit_index[n] で左から順にシグナル番号を記録していく
			start = 0	# Rt でソートしたので開始点まで飛ばせる
			start_flag = 0
			average_mz = library_ave_mz[p]
			peak_rt_early = library_rt_start[p]
			peak_rt_later = library_rt_end[p]
			
			for i in range(0,show_signals,100):		# 枠に入りそうなところまで飛ばす。100刻みで飛ばす
				if(sorted_array_rt[i] > peak_rt_early - rtgap ):
					start = i-100					# 100刻みだと通り過ぎるから戻す。
					if(start < 0): start = 0		# 最初の100で枠に入ってた場合
					break
			for i in range(start,show_signals):		# さらに1刻みで飛ばしてスタート地点まで行く
				if(sorted_array_rt[i] > peak_rt_early - rtgap):
					if(abs(sorted_array_mz[i] - average_mz) < search_mz_width/2):	# 枠に入ったら
						start = i
						break
				if(sorted_array_rt[i] > peak_rt_later + rtgap):		# 通り過ぎちゃったらデータ内に該当シグナルなし
					start = i		# ピーク右端をスタートにする。
					break
			if(sorted_array_rt[start] < peak_rt_later + rtgap):
				prev_rt = sorted_array_rt[start]		# スタート地点を初期値とする
				topsignal_index = index_array[start]
				topsignal = data_it[f][topsignal_index]
				for i in range(start, show_signals):	# ソートしただけなので最大はshow_signalsのはず
					if(abs(sorted_array_mz[i] - average_mz) < search_mz_width/2):	# 枠に入ったら
						if(prev_rt + rtgap < sorted_array_rt[i]):	# 次のScanかどうか判定。rtが+rtgap分以上ずれたら次のscan。
							hit_index.append(topsignal_index)	# 前のScanでみつけたやつを登録
							prev_rt = sorted_array_rt[i]
							topsignal_index = index_array[i]
							topsignal = data_it[f][topsignal_index]
						else:
							if(topsignal < data_it[f][index_array[i]]):
								topsignal_index = index_array[i]
								topsignal = data_it[f][topsignal_index]
					if(sorted_array_rt[i] > peak_rt_later + rtgap):	# 通り過ぎたらおわり
						hit_index.append(topsignal_index)	# 最後のScanでみつけたやつはここで登録
						break
			library_signalindex[p][f] = hit_index


# カーソルに目盛線がついていくようにする
scaleline_vertex = np.zeros(6*(int(maxrt)+int(maxmz/100)+1), dtype = np.float32)	# vbo用のNumpy array
scale_mode = 1		# m/z値の目盛りの刻みを覚えておくglobal変数。
mz_step_list = [2, 10, 40, 100, 200]
rt_step_list = [1, 2, 5, 10, 20]		# 単位は min でなく 0.1min。注意。
def dynamic_zoom():
	global scale_mode
	global scaleline_vertex
	# まず zoom値に応じて目盛りの種類を変える
	scale_mode_new = 0					# zoom =< 0.25。zoomの最小値は 0.1 = zoom_proximlimit
	if(zoom>0.5):scale_mode_new = 1
	if(zoom>1.2):scale_mode_new = 2
	if(zoom>3.0):scale_mode_new = 3		# zoom値が大きいのは遠い視点のとき。最大値は 20 = zoom_distallimit
	if(zoom>6.0):scale_mode_new = 4
	
	if(scale_mode != scale_mode_new):	# 前と違ったら目盛りの種類を切り替えてVBO用の配列を作り直す
		scale_mode = scale_mode_new
		scalelist = []
		for r in range(0, int(maxrt*10), rt_step_list[scale_mode]):		# forは整数でステップしたいから仕方なく。
			rr = r/10
			x = rr / maxrt * field - field_size
			y1 = 0 / maxmz *field - field_size
			y2 = maxmz/maxmz*field- field_size
			scalelist += [x,y1,0,x,y2,0]
		for m in range(0, int(maxmz), mz_step_list[scale_mode]):
			y = m / maxmz * field - field_size
			x1 = 0/ maxrt * field - field_size
			x2 = maxrt/maxrt*field- field_size
			scalelist += [x1,y,0,x2,y,0]
		scaleline_vertex =  np.array(scalelist, dtype=np.float32)	# なぜか初期化なしで動いている

#dynamic_zoom()	# __main__で最初に一回呼ぶ


# VBO 描画部分が全部同じなので関数化して行数を節約
def draw_vbo(array):
	vbo = GLuint(0)
	glGenBuffers(1,vbo)
	glBindBuffer(GL_ARRAY_BUFFER, vbo)
	glBufferData(GL_ARRAY_BUFFER, sys.getsizeof(array), array, GL_STATIC_DRAW)
	glBindBuffer(GL_ARRAY_BUFFER, vbo)
	glEnableClientState(GL_VERTEX_ARRAY)
	glVertexPointer(3, GL_FLOAT, 0, ctypes.cast(0, ctypes.c_void_p))
	glBindBuffer(GL_ARRAY_BUFFER, vbo)
	glDrawArrays(GL_LINES, 0, int(array.size/3))
	glDisableClientState(GL_VERTEX_ARRAY)
	glDeleteBuffers(1,vbo)

# アニメーションモードになったら定期的に描画フラグを立てる。threadingで常時稼働
def animation_driver():
	while(True):
		if(animation_mode == 1):
			glutPostRedisplay()
			time.sleep(0.015)	# リフレッシュレート60 fps だとしたら １フレームあたり 16.6 ミリ秒
		else:
			time.sleep(0.3)		# アニメーションモードがOFFのときは何もしないで休んどく

# 描画関数。ほぼメイン
animation_mode = 0			# 指定ファイルのみoverlayして表示=0; アニメーションする=1
animation_oscilator = 0		# 現在の表示ファイル番号。
animation_direction = 1		# めくる方向
animation_timecounter = time.time()	# アニメーション用の時間カウンター
animation_speed = 0.10		# アニメーション速度。単位は秒。time.time()で返ってくるやつ。
#animation_order = []		# ユーザー指定の順番。どういうふうに指定しようか。。
#animation_orders= 0

# 地面の図形。頂点座標とか色とか。draw関数の中に入れたくないので別の関数にした都合でglobal
fields = float(0 - field_size)
fieldl = float(0 + field_size)
field_vertex = [[fields, fields, 0.0],[fieldl, fields, 0.0],[fieldl, fieldl, 0.0],[fields, fieldl, 0.0]]
field_vcolor = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[1,1,1,0]]	# カラフルにしてみたいとき
cursor_size = 200		# カーソル円の大きさ。割り算するのでこの値が小さいほど大きい。

def draw():
	
	global animation_oscilator
	global animation_direction
	global animation_timecounter
	
	# スクリーンを初期化
	glClearColor(0.0,0.0,0.0,0.0)
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()
	
	# カメラの位置
	camera_x = dist * zoom * math.cos(rotate_vertical) * math.sin(rotate_horizontal) + cx
	camera_y = dist * zoom * math.cos(rotate_vertical) * math.cos(rotate_horizontal) + cy
	camera_z = dist * zoom * math.sin(rotate_vertical)
	camera_posi = [camera_x, camera_y, camera_z]
	camera_target = [cx, cy, 0.0]
	camera_axis = [0.0, 0.0, 1.0]
	camera = camera_posi + camera_target + camera_axis
	gluLookAt(*camera)		# 配列を展開してから引数として渡すときは*を付けるらしい
	
	# 地面
	glBegin(GL_POLYGON)
	glColor(field_color)
	for i in range(0,4):
#		glColor(field_vcolor[i])	# カラフルにするとき
		glVertex(field_vertex[i])
	glEnd()
	
	# 目盛線
	glColor(0.5,0.5,0.5,0.5)
	draw_vbo(scaleline_vertex)
	
	# 目盛の数字
	selected_rt = (cx + field_size) / field * maxrt		# 現在のカーソル位置をrt,mzに変換
	selected_mz = (cy + field_size) / field * maxmz
	rt_step = rt_step_list[scale_mode]/10		# 起点
	mz_step = mz_step_list[scale_mode]
#	if(scale_mode==0):mz_step=mz_step_list[1]	# 一番寄ったとき。目盛線は1刻みだけど目盛りは5刻みでOK
	start_step = 1
	if(scale_mode < 2):start_step = 0
	start_rt = int((selected_rt - rt_step * start_step) /rt_step) * rt_step	# なんかバグってる。以前この定数は6だったけどなんでなのかは複雑すぎてわからない
	start_mz = int((selected_mz - mz_step * 2) /mz_step) * mz_step
	glColor(0.5,0.5,0.5)	# 色
	for r in range(int(start_rt*10), int((start_rt + rt_step*5)*10), int(rt_step*10)):
		rr = r/10	# for のためにrtは10倍のint扱いで処理したのでここで10で割る
		x = rr / maxrt * field - field_size
		y = start_mz / maxmz * field - field_size
		z = 0
		glRasterPos3f(x,y,z)
		for t in str(rr):
			glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(t))
	for m in range(start_mz + mz_step*0, start_mz + mz_step*6, mz_step):
		x = (start_rt -rt_step) / maxrt * field - field_size
		y = m / maxmz * field - field_size
		z = 0
		glRasterPos3f(x,y,z)
		for t in str(m):
			glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(t))
	
	# カーソル。マルの中に向きを表すマルを描く。
	circle_resolution = 32
	eye_resolution = 8
	cursor_data=[]
	cursor_eye =[]
	for i in range(0,circle_resolution):
		rad = math.pi*2/circle_resolution*i
		cursor_data.append([])
		cursor_data[i].append(math.cos(rad) * zoom / cursor_size +cx )
		cursor_data[i].append(math.sin(rad) * zoom / cursor_size +cy )
		cursor_data[i].append(0.01 * zoom / cursor_size )
	for i in range(0,eye_resolution):
		rad = math.pi*2/eye_resolution*i
		cursor_eye.append([])
		cursor_eye[i].append((math.cos(rad) + math.cos(angle)*2) * zoom / cursor_size /4 + cx)
		cursor_eye[i].append((math.sin(rad) + math.sin(angle)*2) * zoom / cursor_size /4 + cy)
		cursor_eye[i].append(0.01 * zoom / cursor_size )
	glColor(0.2, 0.7, 0.7)
	glBegin(GL_LINE_LOOP)
	for i in range(0,circle_resolution):
		glVertex(cursor_data[i])
	glEnd()
	glBegin(GL_POLYGON)
	for i in range(0,eye_resolution):
		glVertex(cursor_eye[i])
	glEnd()
	
	# シグナル（メインデータ）を表示。表示モードで変える。
	if(animation_mode == 0):
		for f in show_file:
			if(len(signal_vertex)>f):		# load_pingがthreading でset_signal を呼んでるのでラグが発生して存在しない配列を呼ぶ瞬間があった
				glColor(file_color_trans[f])
#			a = np.array(signal_vertex[f], dtype=np.float32)	# 型は合ってるが何故か改めてnp.arrayが必要。
#			draw_vbo(a)
				draw_vbo(signal_vertex[f])
	if(animation_mode == 1):
		if(time.time() - animation_timecounter > animation_speed):
			animation_timecounter = time.time()
			animation_oscilator += animation_direction				# oscilator を直接ファイル番号として使っている。
			if(animation_oscilator<0):animation_oscilator=files-1	# オーダー配列を作ってマニュアル設定にするほうがいいかも。
			if(animation_oscilator>files-1):animation_oscilator=0
		f = animation_oscilator
		if(len(signal_vertex)>f):		# load_pingがthreading でset_signal を呼んでるのでラグが発生して存在しない配列を呼ぶ瞬間があった
			glColor(file_color_vivid[f])
#			a = np.array(signal_vertex[f], dtype=np.float32)
#			draw_vbo(a)
			draw_vbo(signal_vertex[f])
			glColor(1.0,1.0,1.0)		# アニメーションモードのときは中央にファイル名を表示する
#			label = filename[f]
			label = str(file_timefactor[f])		# 時間を表示
#			label = str(f) + ' ' + label
			glRasterPos3f(cx,cy,0)
			font = GLUT_BITMAP_HELVETICA_18
			for t in label:
				glutBitmapCharacter(font, ord(t))
	
	# ライブラリを表示
	glColor(0.2, 0.8, 0.8, 1.0)
	draw_vbo(library_square_vertex)
	
	# ライブラリのトップに文字を表示
	glColor(0.2, 0.8, 0.8, 1.0)
	for i in range(0,library_peaks):
		x = library_draw_rt[i] / maxrt * field - field_size
		y = library_draw_mz[i] / maxmz * field - field_size
		z = library_draw_it[i] * skyheight
		label = str(int(library_ave_mz[i] *10000)/10000)
		label = library_label[i] + ' ' + label
		glRasterPos3f(x,y,z)
		font = GLUT_BITMAP_HELVETICA_18
		if(zoom > 3.5):
			font = GLUT_BITMAP_HELVETICA_12
		for t in str(label):
			glutBitmapCharacter(font, ord(t))
	
	# 屏風を表示
	if(library_peaks>0):
		for f in range(0,files):
			if(len(library_vertex[f])>0):
				glColor(file_color_vivid[f])
				draw_vbo(library_vertex[f])		# ここでは直前でnumpy化する必要がないらしい。謎
	
	glutSwapBuffers()

# ポップアップメニューの応答。メニューの設定と離れてると変えるとき面倒なので関数にして並べとく
def pulldownmenu(item):
	global animation_mode
	if(item == 0): pass
	if(item == 1): peak_select()
	if(item == 2): peak_delete()
	if(item == 3): export_data()
	if(item == 4): peak_delete_all()
	if(item == 5): peak_select_auto()
	if(item == 6): pass
	if(item == 7): pass
	if(item == 8): calibration_rt()
	if(item == 9): calibration_rt_large()
	if(item ==10): calibration_reset_rt()
	if(item ==11): calibration_mz()
	if(item ==12): calibration_reset_mz()
	if(item ==13): pass
	if(item ==14): pass
	if(item ==15): animation_mode = 1-animation_mode
	if(item ==16): align_straight()
	if(item ==17): os._exit(0)
	return(0)
def set_pulldownmenu():
	menutext = ['< peak assignment >',
				'assign a peak in cursor [space bar]',
				'clear a peak in cursor [shift + space bar]',
				'export peak volume data to a file',
				'clear all peak assignment',
				'automatic assign (not recommended)',
				'',
				'< calibration >',
				'align time axis',
				'align LC condition (select two pair of peaks)',
				'reset time axis alignment',
				'calibrate m/z detection',
				'reset m/z calibration ',
				'',
				'< animation >',
				'animation mode ON/OFF',
				'align camera angle',
				'close GrassHopper [q]'	]
	selectmenu = glutCreateMenu(pulldownmenu)		# プルダウンメニュー
	glutAddMenuEntry(menutext[0], 0)
	glutAddMenuEntry(menutext[1], 1)	# 何故かCreateMenuの返り値を与えられない（与えなくても機能してる不思議）
	glutAddMenuEntry(menutext[2], 2)
	glutAddMenuEntry(menutext[3], 3)
	glutAddMenuEntry(menutext[4], 4)
	glutAddMenuEntry(menutext[5], 5)
	glutAddMenuEntry(menutext[6], 6)
	glutAddMenuEntry(menutext[7], 7)
	glutAddMenuEntry(menutext[8], 8)
	glutAddMenuEntry(menutext[9], 9)
	glutAddMenuEntry(menutext[10],10)
	glutAddMenuEntry(menutext[11],11)
	glutAddMenuEntry(menutext[12],12)
	glutAddMenuEntry(menutext[13],13)
	glutAddMenuEntry(menutext[14],14)
	glutAddMenuEntry(menutext[15],15)
	glutAddMenuEntry(menutext[16],16)
	glutAddMenuEntry(menutext[17],17)
	glutAttachMenu(GLUT_RIGHT_BUTTON)

# リサイズ。
zoom_distallimit = 20.0		# カメラからの有効距離範囲。遠い方の限界
zoom_proximlimit = 0.02			# カメラからの有効距離範囲。近い方の限界
lens_factor  = 10.0				# 遠近法の表現の激しさ。小さいと望遠レンズ、大きいと広角レンズ。
window_width = 900			# ウィンドウの横幅 マウス入力のとき使う
window_height = 600			# ウィンドウの縦幅 マウス入力のとき使う
def resize(width,height):
	global window_width
	global window_height
	window_width = width
	window_height= height
	glViewport(0,0,width,height)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	gluPerspective(lens_factor, width/height, zoom_proximlimit*0.5, zoom_distallimit*1.2)	# ちょっと広くする
	glMatrixMode(GL_MODELVIEW)
	glutPostRedisplay()


# ジョイスティック入力
camera_rotate_grid = 2		# カメラ位置をまっすぐの位置にする。1だと90度単位。2だと45度単位
camera_rotate_speed = 0.025	# フィールドを回す速さ。大きいほど速い
stick_speed_z = 50000		# アナログスティックでの動きの速さ。仰角の速度。大きいほど遅い
stick_speed_xy = 800000		# アナログスティックでの動きの速さ。水平方向の移動速度。大きいほど遅い
stick_x_zero = 0
stick_y_zero = 0		# アナログスティックのゼロ点を覚えておくためのglobal変数
stick_z_zero = 0
def joystick(joy, x, y, z):

	global zoom
	global angle
	global rotate_horizontal
	global rotate_vertical
	global stick_x_zero
	global stick_y_zero
	global stick_z_zero
	global cx
	global cy
	
	# ボタンが押されたときの応答
	if(joy > 0):
		if(joy & 128):				# R2/L2 ボタンを拡大・縮小に割り当ててみる
			zoom = zoom * 0.98
			if(zoom < zoom_proximlimit):
				zoom = zoom_proximlimit
			dynamic_zoom()
		if(joy & 64):
			zoom = zoom * 1.02
			if(zoom > zoom_distallimit):
				zoom = zoom_distallimit
			dynamic_zoom()
		if(joy & 32):				# R1/L1 ボタンを回転に割り当ててみる
			rotate_horizontal += camera_rotate_speed
			if(rotate_horizontal > 2* math.pi):
				rotate_horizontal = 0
		if(joy & 16):				# R1/L1 ボタンを回転に割り当ててみる
			rotate_horizontal -= camera_rotate_speed
			if(rotate_horizontal < 0):
				rotate_horizontal = 2* math.pi
		if(joy & 1):				# ボタン１は直角から見るボタン。PlayStationの四角ボタン
			r = int((rotate_horizontal+math.pi/4/camera_rotate_grid)/2/math.pi*4*camera_rotate_grid)
			rotate_horizontal = r*math.pi/2/camera_rotate_grid
		if(joy & 2048):				 # start ボタンをジョイスティックのリセットボタンにする
			stick_x_zero = x * (-1)
			stick_y_zero = y * (-1)
			stick_z_zero = z * (-1)
		if(joy & 8):
			peak_select()
		if(joy & 4):
			peak_delete()
		if(joy & 2):
			calibration_rt()
			calibration_mz()
		if(joy & 1024):				 # select ボタンをcalibrationのリセットボタンにする
			calibration_reset_rt()
			calibration_reset_mz()
		
	# アナログスティックの応答
	stick_x = x + stick_x_zero		# ゼロ補正。
	stick_y = y + stick_y_zero
	stick_z = z + stick_z_zero
	if(abs(stick_z) > abs(stick_x) + abs(stick_y) + 80):	# 機種依存かも。xがzにも乗ってる。yがzに乗る機種もあるかも？。あとzは何故か-27くらいにいつも傾いてる
		rotate_vertical += stick_z/stick_speed_z	# 折角アナログなので強さも反映してみる
		if(rotate_vertical > math.pi/2 - rotate_vertical_limit_sky):
			rotate_vertical = math.pi/2 -rotate_vertical_limit_sky
		if(rotate_vertical < rotate_vertical_limit_ground):
			rotate_vertical = rotate_vertical_limit_ground
	if(abs(stick_x) + abs(stick_y) > 10):	# xとyは最初からちょっと傾いてる。各3くらい。機種依存かも。
		angle = math.atan2(stick_y,(-1)*stick_x) - rotate_horizontal	# スティックの傾き角度(ラジアン)
		strength = math.sqrt(stick_x * stick_x + stick_y * stick_y)/stick_speed_xy	# スティックの傾き具合
		cx = cx + math.cos(angle) * strength*zoom	# 移動方向の計算。
		cy = cy + math.sin(angle) * strength*zoom	# ズーム値を掛け算。
		if(abs(cy)>field_size): cy = cy/abs(cy)*field_size
		if(abs(cx)>field_size): cx = cx/abs(cx)*field_size	# はみ出ないようにする
	
	glutPostRedisplay()

def align_straight():
	global rotate_horizontal
	r = int((rotate_horizontal+math.pi/4/camera_rotate_grid)/2/math.pi*4*camera_rotate_grid)
	rotate_horizontal = r*math.pi/2/camera_rotate_grid


# マウス入力。glutMouseFuncからだと押したら一回だけしか呼ばれないのでglutMotionFuncの方にした
#def mouse(button, state, x, y):
def mouse_dragging(x, y):
#	if(button == GLUT_LEFT_BUTTON):
	if(True):
#		if(state == GLUT_DOWN):
		if(True):
			xx = x/window_width
			yy = y/window_height
			grid = 0.25
			margin = 0.05
			grid_a = grid
			grid_b = grid + margin
			grid_c = 1 - grid - margin
			grid_d = 1 - grid
			if(yy < grid):
				if(xx < grid_a):					# 左上
					pass		# m/z軸を広げるキーにする予定
				if(xx > grid_b and xx < grid_c):	# 上
					camera_vertical(1000 * (grid_a-yy) / grid)
				if(xx > grid_d):					# 右上
					zoom_res(0.98)
			if(yy > grid_b and yy < grid_c):
				if(xx < grid_a):					# 左
					camera_horizontal(-1)
				if(xx > grid_b and xx < grid_c):	# 中央
					square = window_height
					if(square > window_width):
						square = window_width
					square /= 3
					xxx = 1000*(x-window_width/2)/square
					yyy = 1000*(y-window_height/2)/square
					cursor_move(xxx,yyy)
				if(xx > grid_d):					# 右
					camera_horizontal(1)
			if(yy > grid_d):
				if(xx < grid_a):					# 左下
					pass		# m/z軸を戻すキーにする予定
				if(xx > grid_b and xx < grid_c):	# 下
					camera_vertical(1000 * (yy-grid_d) /grid * (-1))
				if(xx > grid_d):					# 右下
					zoom_res(1.02)
	glutPostRedisplay()

# キーボードの上下左右とshift, ctrl, alt
def keyboard_special(key, x, y):
	mod = glutGetModifiers()
	speed = 3
	if(mod == 0):
		if(key == GLUT_KEY_UP):		cursor_move(0,-1000*speed)
		if(key == GLUT_KEY_DOWN):	cursor_move(0, 1000*speed)
		if(key == GLUT_KEY_LEFT):	cursor_move(-1000*speed,0)
		if(key == GLUT_KEY_RIGHT):	cursor_move( 1000*speed,0)
	if(mod & GLUT_ACTIVE_SHIFT):
		if(key == GLUT_KEY_UP):		camera_vertical( 1000*speed)
		if(key == GLUT_KEY_DOWN):	camera_vertical(-1000*speed)
		if(key == GLUT_KEY_LEFT):	camera_horizontal(-1*speed)
		if(key == GLUT_KEY_RIGHT):	camera_horizontal( 1*speed)
	if(mod & GLUT_ACTIVE_ALT):
		if(key == GLUT_KEY_UP):		zoom_res(1 + 0.02*speed)
		if(key == GLUT_KEY_DOWN):	zoom_res(1 - 0.02*speed)
		if(key == GLUT_KEY_LEFT):	pass
		if(key == GLUT_KEY_RIGHT):	pass
	glutPostRedisplay()

# ユーザー入力で3DCG画面を操作する関数群。
def camera_vertical(stick_z):
	global rotate_vertical
	rotate_vertical += stick_z/stick_speed_z	# 折角アナログなので強さも反映してみる
	if(rotate_vertical > math.pi/2 - rotate_vertical_limit_sky):
		rotate_vertical = math.pi/2 -rotate_vertical_limit_sky
	if(rotate_vertical < rotate_vertical_limit_ground):
		rotate_vertical = rotate_vertical_limit_ground

def zoom_res(direction):
	global zoom
	zoom = zoom * direction
	if(zoom < zoom_proximlimit):
		zoom = zoom_proximlimit
	if(zoom > zoom_distallimit):
		zoom = zoom_distallimit
	dynamic_zoom()

def camera_horizontal(direction):
	global rotate_horizontal
	rotate_horizontal += camera_rotate_speed * direction
	if(rotate_horizontal > 2* math.pi):
		rotate_horizontal = 0
	if(rotate_horizontal < 0):
		rotate_horizontal = 2* math.pi

def cursor_move(x,y):
	global angle
	global cx
	global cy
	angle = math.atan2(y,(-1)*x) - rotate_horizontal	# スティックの傾き角度(ラジアン)
	strength = math.sqrt(x * x + y * y)/stick_speed_xy	# スティックの傾き具合
	cx = cx + math.cos(angle) * strength*zoom	# 移動方向の計算。
	cy = cy + math.sin(angle) * strength*zoom	# ズーム値を掛け算。
	if(abs(cy)>field_size): cy = cy/abs(cy)*field_size
	if(abs(cx)>field_size): cx = cx/abs(cx)*field_size	# はみ出ないようにする

# キーボード
def keyboard(key, x, y):
	if(key == b' '):
		mod = glutGetModifiers()
		if(mod & GLUT_ACTIVE_SHIFT):peak_delete()
		else:peak_select()
	if(key == b'q'): os._exit(0)		# プログラムを終了
	glutPostRedisplay()

# キーボード。テスト用
def keyboard_(key, x, y):
	global zoom
	global animation_mode
	if(key == b'q'): os._exit(0)		# プログラムを終了
	if(key == b'z'): zoom *= 1.1		# カメラを遠くする。ジョイスティックつなぎ忘れたとき面倒だったから。
	if(key == b'x'): zoom *= 0.9		# カメラを近くする
	if(key == b's'): set_signal()		# テスト
	if(key == b'a'): animation_mode = 1-animation_mode
	if(key == b'd'): peak_delete_all()
	if(key == b'u'): peak_select_auto()
	if(key == b'c'): calibration_rt()
	if(key == b'n'): calibration_rt_large()
	if(key == b'v'): calibration_mz()
	if(key == b'b'): calibration_reset_rt()
	if(key == b'b'): calibration_reset_mz()
	if(key == b'p'): export_data()
	glutPostRedisplay()
	


argv()	# 一回呼ぶ
print(project)
print(projectfilepass)	# 受け取れてるかテスト
print(datafilepass)
print(exportfilepass)
print(pingfilepass)
data_loader()	# 一回呼ぶ。テスト
load_standards()	# 一回呼ぶ
set_signal()	# 一回呼ぶ
dynamic_zoom()	# __main__で最初に一回呼ぶ


# メイン関数に相当する部分
glutInit(sys.argv)
glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
glutInitWindowSize(900,600)			# window の初期サイズ
glutCreateWindow("GrassHopper - an LCMS Data Analyser : " + project)	# これはバーに表示するソフトの名前のようだ
glEnable(GL_DEPTH_TEST)				# 裏側に隠れた部分を表示しない機能
glEnable(GL_BLEND)					# 透過処理を有効化
glBlendFunc(GL_SRC_ALPHA, GL_ONE)	# 透過処理の内容を記号で指定するらしい
glutDisplayFunc(draw)				# 描画関数。glutPostRedisplay でフラグが立ったら呼ばれるっぽい
glutReshapeFunc(resize)				# リサイズ時の応答を関数。GUIからのコールバック関数みたいに設定するらしい
glutKeyboardFunc(keyboard)			# キーボードが押されたとき応答する関数を指定する
glutSpecialFunc(keyboard_special)	# キーボードの上下左右シフトキーとか。
glutJoystickFunc(joystick, 10)		# ジョイスティックをモニターする。何ミリ秒に一回見に行くかを数値で指定する
#glutIdleFunc(demo)
#glutMouseFunc(mouse)
glutMotionFunc(mouse_dragging)

set_pulldownmenu()	# ポップアップメニューの設定。glutの設定の後で一回だけ呼ぶ

# マルチスレッドで常駐する関数
ping_dat = 0
ping_file = 0
ping_std = 0
ping_export = 0
send_ping()
thread1 = threading.Thread(target = load_ping)	# pingを見に行く無限ループ
thread1.setDaemon(True)
thread1.start()

thread2 = threading.Thread(target = animation_driver)
thread2.setDaemon(True)
thread2.start()


glutMainLoop()



