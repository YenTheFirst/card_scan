import math
import cv
import os
import sqlite3
import numpy
import cv2

debug_status = None

#**************************
#this is the 'detect card' bit
def find_longest_contour(contour_seq):
	x = contour_seq
	max_len = 0
	max = None
	try:
		while x is not None:
			if cv.ArcLength(x) > max_len:
				max_len = cv.ArcLength(x)
				max = x
			x = x.h_next()
	except:
		pass
	return (max, max_len)


def longest_lines(hull):
	l = len(hull)
	lines = [0] * l
	for n in xrange(l):
		x1, y1 = hull[n]
		x2, y2 = hull[(n+1) % l]
		lines[n] = {
			'c1': (x1, y1),
			'c2': (x2, y2),
			'len': ( (x2-x1)**2 + (y2-y1)**2 ) ** 0.5,
			'angle': math.atan2(y2 - y1, x2-x1),
		}
	#make straight-ish lines actually straight
	n = 0
	while n+1 < len(lines):
		l1 = lines[n]
		l2 = lines[(n+1) % len(lines)]
		if abs(l1['angle'] - l2['angle']) / (math.pi*2) < 0.0027:
			x1, y1 = c1 = l1['c1']
			x2, y2 = c2 = l2['c2']
			lines[n] = {
				'c1': c1,
				'c2': c2,
				'len': ( (x2-x1)**2 + (y2-y1)**2 ) ** 0.5,
				'angle': math.atan2(y2 - y1, x2-x1),
			}
			del lines[n+1]
		else:
			n += 1

	lines.sort(key = lambda l: -l['len'])
	return lines

def line_intersect(s1, s2):
	#just copied from wikipedia :)
	x1, y1 = s1['c1']
	x2, y2 = s1['c2']
	x3, y3 = s2['c1']
	x4, y4 = s2['c2']

	denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
	if denom == 0:
		return None
	x = ((x1*y2 - y1*x2)*(x3-x4) - (x1-x2)*(x3*y4 - y3*x4)) / float(denom)
	y = ((x1*y2 - y1*x2)*(y3-y4) - (y1-y2)*(x3*y4 - y3*x4)) / float(denom)

	return (int(round(x)),int(round(y)))


def detect_card(grey_image, grey_base, thresh=100):
	if debug_status == "grey":
		tmp = cv.CloneImage(grey_image)
		cv.PutText(tmp, "greyscale", (1,24), font, 0)
		cv.ShowImage('debug', tmp)
		return None

	if debug_status == "base":
		tmp = cv.CloneImage(grey_base)
		cv.PutText(tmp, "baseline", (1,24), font, 0)
		cv.ShowImage('debug', tmp)
		return None

	diff = cv.CloneImage(grey_image)
	cv.AbsDiff(grey_image, grey_base, diff)
	if debug_status == "diff":
		cv.PutText(diff, "difference", (1,24), font, 255)
		cv.ShowImage('debug', diff)
		return None

	edges = cv.CloneImage(grey_image)
	cv.Canny(diff, edges, thresh, thresh)
	if debug_status == "edges":
		cv.PutText(edges, "edges", (1,24), font, 255)
		cv.ShowImage('debug', edges)
		return None

	contours = cv.FindContours(edges, cv.CreateMemStorage(0))
	edge_pts = []
	if debug_status == "contours":
		tmp = cv.CloneImage(grey_image)
		c = contours 
		while c is not None:
			if len(c) > 20:
				cv.DrawContours(tmp, c, 255, 255, 0)
			c = c.h_next()
		cv.PutText(tmp, "contours", (1,24), font, 0)
		cv.ShowImage('debug', tmp)
		return None

	c = contours
	while c is not None:
		if len(c) > 20:
			edge_pts += list(c)
		if len(c) == 0: #'cus opencv is buggy and dumb
			break
		c = c.h_next()

	if len(edge_pts) == 0:
		return None

	if debug_status == "edge_points":
		tmp = cv.CloneImage(grey_image)
		for pt in edge_pts:
			cv.Circle(tmp, pt, 1, 255)
		cv.PutText(tmp, "edge points", (1,24), font, 0)
		cv.ShowImage('debug', tmp)
		return None

	hull = cv.ConvexHull2(edge_pts, cv.CreateMemStorage(0), cv.CV_CLOCKWISE, 1)
	if debug_status == "hull":
		tmp = cv.CloneImage(grey_image)
		cv.PolyLine(tmp, [hull], True, 255, 2)
		cv.PutText(tmp, "convex hull", (1,24), font, 0)
		cv.ShowImage('debug', tmp)
		return None

	lines = longest_lines(hull)
	perim = sum(l['len'] for l in lines)
	print perim

	if debug_status == "longest_lines":
		tmp = cv.CloneImage(grey_image)
		for l in lines[0:4]:
			cv.Line(tmp, l['c1'], l['c2'], 255, 2)
		cv.PutText(tmp, "longest lines", (1,24), font, 0)
		cv.ShowImage('debug', tmp)
		return None

	#likely to be a card. . .
	#if abs(perim - 1200) < 160:
	if perim > 700:
		#extrapolate the rectangle from the hull.
		#if our 4 longest lines make up 80% of our perimiter
		l = sum(l['len'] for l in lines[0:4])
		print "l = ",l
		if l / perim  >0.8:
			#we probably have a high-quality rectangle. extrapolate!
			sides = sorted(lines[0:4], key = lambda x: x['angle'])
			#sides are in _some_ clockwise order.
			corners = [None]*4
			for n in xrange(4):
				corners[n] = line_intersect(sides[n], sides[(n+1) % 4])
			if not all(corners):
				return None

			if debug_status == "corners":
				tmp = cv.CloneImage(grey_image)
				for c in corners:
					cv.Circle(tmp, c, 4, 255)
				cv.PolyLine(tmp, [corners], True, 255, 2)
				cv.PutText(tmp, "area to extract", (1,24), font, 0)
				cv.ShowImage('debug', tmp)
				return None

			#rotate corners so top-left corner is first. 
			#that way we're clockwise from top-left
			sorted_x = sorted(c[0] for c in corners)
			sorted_y = sorted(c[1] for c in corners)
			top_left = None
			for index, (x,y) in enumerate(corners):
				if sorted_x.index(x) < 2 and sorted_y.index(y) < 2:
					top_left = index
			if top_left is None:
				return None
			#return rotated list
			return corners[top_left:] + corners[:top_left]

	return None

def get_card(color_capture, corners):
	target = [(0,0), (223,0), (223,310), (0,310)]
	mat = cv.CreateMat(3,3, cv.CV_32FC1)
	cv.GetPerspectiveTransform(corners, target, mat)
	warped = cv.CloneImage(color_capture)
	cv.WarpPerspective(color_capture, warped, mat)
	cv.SetImageROI(warped, (0,0,223,310) )
	return warped

def draw_keypoints(color_img, keypoints):
	tmp = cv.CloneImage(color_img)
	min_size = min(size for (pt, l, size, dir, hessian) in keypoints)
	max_size = max(size for (pt, l, size, dir, hessian) in keypoints)
	min_length = 2
	max_length = 10
	ratio = (max_length - min_length) / float(max_size - min_size)

	for ((x,y), lap, size, dir, hessian) in keypoints:
		p1 = (int(x), int(y))
		if lap==1:
			color = (255,0,0)
		elif lap==0:
			color = (0,255,0)
		elif lap==-1:
			color = (0,0,255)
		else:
			color = (255, 255, 255) # shouldn't happen

		length = (size - min_size) * ratio + min_length

		cv.Circle(tmp, p1, 1, color)
		a = math.pi * dir / 180.0
		p2 = (
			int(x + math.cos(a) * length),
			int(y + math.sin(a) * length)
		)
		cv.Line(tmp, p1, p2, color)
	return tmp


def float_version(img):
	tmp = cv.CreateImage( cv.GetSize(img), 32, 1)
	cv.ConvertScale(img, tmp, 1/255.0)
	return tmp

def mask_for(img, pt):
	tmp = cv.CreateImage( cv.GetSize(img), 8, 1)
	cv.Set(tmp, 255)
	cv.Rectangle(tmp, (0,0), pt, 0, -1)
	return tmp

def high_freq(img, pct):
	f = float_version(img)
	cv.DFT(f, f, cv.CV_DXT_FORWARD)
	mask = cv.CreateImage( cv.GetSize(img), 8, 1)
	cv.Set(mask, 0)
	#cv.Set(mask, 255)
	w, h = cv.GetSize(img)
	dw = int(w*pct*0.5)
	dh = int(h*pct*0.5)
	#cv.Rectangle(mask, (0,0), (int(w*pct), int(h*pct)), 255, -1)
	#cv.Rectangle(mask, (int(w*pct), int(h*pct)), (w,h), 255, -1)
	cv.Rectangle(mask, (w/2-dw,h/2-dh), (w/2+dw,h/2+dh), 255, -1)
	cv.Set(f,0,mask)
	return f
	cv.DFT(f, f, cv.CV_DXT_INVERSE_SCALE)
	return f


def sum_squared(img1, img2):
	tmp = cv.CreateImage(cv.GetSize(img1), 8,1)
	cv.Sub(img1,img2,tmp)
	cv.Pow(tmp,tmp,2.0)
	return cv.Sum(tmp)[0]

def ccoeff_normed(img1, img2):
	size = cv.GetSize(img1)
	tmp1 = float_version(img1)
	tmp2 = float_version(img2)

	cv.SubS(tmp1, cv.Avg(tmp1), tmp1)
	cv.SubS(tmp2, cv.Avg(tmp2), tmp2)

	norm1 = cv.CloneImage(tmp1)
	norm2 = cv.CloneImage(tmp2)
	cv.Pow(tmp1, norm1, 2.0)
	cv.Pow(tmp2, norm2, 2.0)

	#cv.Mul(tmp1, tmp2, tmp1)

	return cv.DotProduct(tmp1, tmp2) /  (cv.Sum(norm1)[0]*cv.Sum(norm2)[0])**0.5



#*****************
#this is the watch-for-card bit
captures = []

def card_window_clicked(event, x, y, flags, param):
	if event == 6:
	#delete capture array indexed at param, update windows
		global captures
		del captures[param]
		update_windows()

def update_windows(n=3):
	print "update windows!"
	l = len(captures)
	for i in xrange(1,4):
		cv.ShowImage("card_%d" % i, None)
	for i in xrange(1,min(n,l)+1):
		print "setting ",i
		tmp = cv.CloneImage(captures[-i])
		cv.PutText(tmp, "%s" % (l-i+1), (1,24), font, (255,255,255))
		cv.ShowImage("card_%d" % i, tmp)
		cv.SetMouseCallback("card_%d" % i, card_window_clicked, l - i)

def watch_for_card(camera):
	has_moved = False
	been_to_base = False

	global captures
	global font
	global debug_status
	captures = []

	font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 1.0, 1.0, thickness=3)
	img = cv.QueryFrame(camera)
	size = cv.GetSize(img)
	n_pixels = size[0]*size[1]

	grey = cv.CreateImage(size, 8,1)
	recent_frames = [cv.CloneImage(grey)]
	base = cv.CloneImage(grey)
	cv.CvtColor(img, base, cv.CV_RGB2GRAY)
	#cv.ShowImage('card', base)
	tmp = cv.CloneImage(grey)


	while True:
		img = cv.QueryFrame(camera)
		cv.CvtColor(img, grey, cv.CV_RGB2GRAY)

		biggest_diff = max(sum_squared(grey, frame) / n_pixels for frame in recent_frames)

		#display the cam view
		cv.PutText(img, "%s" % biggest_diff, (1,24), font, (255,255,255))
		cv.ShowImage('win',img)
		recent_frames.append(cv.CloneImage(grey))
		if len(recent_frames) > 5:
			del recent_frames[0]

		#check for keystroke
		c = cv.WaitKey(10)
		#if there was a keystroke, reset the last capture
		if c == 27:
			return captures
		elif c == 32:
			has_moved = True
			been_to_base = True
		elif c == 114:
			base = cv.CloneImage(grey)
		elif c >= 48 and c <= 57:
			num = c-48
			debug_status = [None, "base", "grey", "diff", "edges", "contours", "edge_points", "hull", "longest_lines", "corners"][num]
			print "debug_status: ",debug_status


		#if we're stable-ish
		if debug_status is not None:
			detect_card(grey, base)
		elif biggest_diff < 10:
			#if we're similar to base, update base
			#else, check for card
			#base_diff = max(sum_squared(base, frame) / n_pixels for frame in recent_frames)
			base_corr = min(ccoeff_normed(base, frame) for frame in recent_frames)
			#cv.ShowImage('debug', base)

			"""for i, frame in enumerate(recent_frames):
				tmp = cv.CloneImage(base)
				cv.Sub(base, frame, tmp)
				cv.Pow(tmp, tmp, 2.0)
				cv.PutText(tmp, "%s" % (i+1), (1,24), font, (255, 255, 255))
				#my_diff = sum_squared(base, frame) / n_pixels
				my_diff = ccoeff_normed(base, frame) #score(base, frame, cv.CV_TM_CCOEFF_NORMED)
				cv.PutText(tmp, "%s" % my_diff, (40, 24), font, (255, 255, 255))
				cv.ShowImage('dbg%s' % (i+1), tmp)"""
			#print "stable. corr = %s. moved = %s. been_to_base = %s" % (base_corr, has_moved, been_to_base)
			if base_corr > 0.75:
				base = cv.CloneImage(grey)
			#	cv.ShowImage('debug', base)
				has_moved = False
				been_to_base = True
			elif has_moved and been_to_base:
				corners = detect_card(grey, base)
				if corners is not None:
					card = get_card(grey, corners)
					cv.Flip(card,card,-1)
					captures.append(card)
					update_windows()
					#cv.ShowImage('card', card)
					has_moved = False
					been_to_base = False
		else:
			has_moved = True


def setup_windows():
	cv.NamedWindow('card_1')
	cv.NamedWindow('card_2')
	cv.NamedWindow('card_3')
	#cv.NamedWindow('base')
	cv.NamedWindow('win')
	#cv.StartWindowThread()



def show_scaled(win, img):
	min, max, pt1, pt2 = cv.MinMaxLoc(img)
	cols, rows = cv.GetSize(img)
	tmp = cv.CreateMat(rows, cols,cv.CV_32FC1)
	cv.Scale(img, tmp, 1.0/(max-min), 1.0*(-min)/(max-min))
	cv.ShowImage(win,tmp)


#**************************
#some utilities to manage card loading/saving
def load_sets(base_dir, set_names):
	cards = []
	for dir, subdirs, fnames in os.walk(base_dir):
		set = os.path.split(dir)[1]
		if set in set_names:
			for fname in fnames:
				path = os.path.join(dir, fname)

				img = cv.LoadImage(path,0)
				if cv.GetSize(img) != (223, 310):
					tmp = cv.CreateImage((223, 310), 8, 1)
					cv.Resize(img,tmp)
					img = tmp
				angle_map = gradient(img)[1]
				hist = angle_hist(angle_map)

				cards.append((
					fname.replace('.full.jpg',''),
					set,
					angle_map,
					hist
				))
	return cards


def img_from_buffer(buffer):
	np_arr = numpy.fromstring(buffer,'uint8')
	np_mat = cv2.imdecode(np_arr,0)
	return cv.fromarray(np_mat)

#cv.EncodeImage('.PNG',img).tostring()
def save_captures(num, captures):
	dir = "capture_%02d" % num
	if not os.path.exists(dir):
		os.mkdir(dir)
	for i, img in enumerate(captures):
		path = os.path.join(dir, "card_%04d.png" % i)
		if os.path.exists(path):
			raise Exception("path %s already exists!" % path)
		cv.SaveImage(path, img)

def folder_to_db(num):
	connection = sqlite3.connect("inventory.sqlite3")
	try:
		cursor = connection.cursor()

		dir = "capture_%02d" % num
		names = sorted(os.listdir(dir))
		for i, name in enumerate(names):
			path = os.path.join(dir, name)
			img = open(path).read()

			cursor.execute('insert into inv_cards (scan_png, box, box_index) values (?, ?, ?)', [sqlite3.Binary(img), num, i])
		connection.commit()
	finally:
		connection.close()

def match_db_cards(known):
	connection = sqlite3.connect("inventory.sqlite3")
	try:
		cursor = connection.cursor()
		cursor.execute("select rowid, scan_png from inv_cards where status = 0")
		row = cursor.fetchone()
		while row is not None:
			try:
				id, buf = row
				img = img_from_buffer(buf)
				card, set = match_card(img, known)
				card = unicode(card.decode('UTF-8'))
				cv.ShowImage('debug', img)
				print "set row %s to %s/%s" % (id, set, card)
				update_c = connection.cursor()
				update_c.execute('update inv_cards set name=?, set_name=?, status = 1 where rowid=?', [card, set, id])
				connection.commit()
			except KeyboardInterrupt as e:
				raise e
			except Exception as e:
				print "failure on row %s" % row[0]
				print e
			finally:
				row = cursor.fetchone()
	finally:
		connection.close()

#*********************
#card matching section
def gradient(img):
	cols, rows = cv.GetSize(img)

	x_drv = cv.CreateMat(rows,cols,cv.CV_32FC1)
	y_drv = cv.CreateMat(rows,cols,cv.CV_32FC1)
	mag = cv.CreateMat(rows,cols,cv.CV_32FC1)
	ang = cv.CreateMat(rows,cols,cv.CV_32FC1)

	cv.Sobel(img, x_drv, 1, 0)
	cv.Sobel(img, y_drv, 0, 1)
	cv.CartToPolar(x_drv,y_drv,mag,ang)
	return (mag,ang)

def angle_hist(mat):
	h = cv.CreateHist([9], cv.CV_HIST_ARRAY, [(0.001,math.pi*2)], True)
	cv.CalcHist([cv.GetImage(mat)], h)
	#cv.NormalizeHist(h,1.0)
	return h

def score(card, known, method):
	r = cv.CreateMat(1, 1, cv.CV_32FC1)
	cv.MatchTemplate(card, known, r, method)
	return r[0,0]

def match_card(card, known_set):
	mag, grad = gradient(card)
	h = angle_hist(grad)
	#limited_set = sorted([(cv.CompareHist(h, hist, cv.CV_COMP_CORREL), name, set, g) for name,set,g,hist in known_set], reverse=True)[0:1000]
	#h_score, name, set, img = max(limited_set,
	#	key = lambda (h_score, name, set, known): score(grad, known, cv.CV_TM_CCOEFF)
	#)
	name, set, g, h = max(known_set,
		key = lambda (n, s, g, h): ccoeff_normed(g,grad)
	)
	return (name, set)

LIKELY_SETS = [
	'DKA', 'ISD',
	'NPH', 'MBS', 'SOM',
	'ROE', 'WWK', 'ZEN',
	'ARB', 'CON', 'ALA',
	'EVE', 'SHM', 'MOR', 'LRW',
	'M12', 'M11', 'M10', '10E',
	'HOP',
]
	

'''
import cv
import scan_card
base = cv.LoadImage("base.png", 0)
known = cv.LoadImage("known/swamp_m12_03.jpg")
capture = cv.LoadImage("swamp_02.png", 0)
corners =  scan_card.detect_card(capture, base)
card = scan_card.get_card(cv.LoadImage("swamp_02.png"), corners)

cv.NamedWindow("win")
cv.StartWindowThread()
cv.ShowImage("win", card)
'''


'''
test 1
base = cv.LoadImage("base.png", 0)
capture = cv.LoadImage("swamp_02.png", 0)
corners =  scan_card.detect_card(capture, base)
corners should not be None
corners should be close to [(253, 44), (503, 44), (530, 400), (244, 402)]


test 2
base = cv.LoadImage("base_03.png", 0)
capture = cv.LoadImage("swamp_03.png", 0)
corners =  scan_card.detect_card(capture, base)
corners should not be none
corners should be close to [(167, 126), (384, 69), (460, 366), (235, 423)]
'''


'''
for dirname, dirnames, filenames in os.walk('known'):
	for filename in filenames:
	path = os.path.join(dirname, filename)
	img = cv.LoadImage(path,0)
	cv.SetImageROI(img, (0,0,223,310))
	known.append( (path, img) )



r = cv.CreateMat(1, 1, cv.CV_32FC1)
'''

'''
import cv
import scan_card
cv.NamedWindow('win')
cv.NamedWindow('base')
cv.NamedWindow('card')
cv.StartWindowThread()
cam = cv.CreateCameraCapture(0)
scan_card.watch_for_card(cam)
'''


'''
cards = scan_card.load_sets(base_dir, ['ISD', 'DKA'])
c2 = [(name, scan_card.gradient(the_card)[1]) for name, the_card in cards]

for i in xrange(9):
    card = cv.LoadImage('captures/card_%04d.png' % i,0)
    cv.ShowImage('card',card); g = scan_card.gradient(card)[1]
    f = sorted([(score(g, the_card_g, cv.CV_TM_CCOEFF), name) for name,the_card_g in c2], reverse=True)[0:5]
    print f
    raw_input()
'''

