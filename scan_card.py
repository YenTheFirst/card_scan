import math
import cv

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
	diff = cv.CloneImage(grey_image)
	cv.AbsDiff(grey_image, grey_base, diff)
	
	edges = cv.CloneImage(grey_image)
	cv.Canny(diff, edges, thresh, thresh)

	contours = cv.FindContours(edges, cv.CreateMemStorage(0))
	edge_pts = []
	c = contours
	while c is not None:
		if len(c) > 10:
			edge_pts += list(c)
		if len(c) == 0: #'cus opencv is buggy and dumb
			break
		c = c.h_next()
	
	if len(edge_pts) == 0:
		return None
	hull = cv.ConvexHull2(edge_pts, cv.CreateMemStorage(0), cv.CV_CLOCKWISE, 1)
	lines = longest_lines(hull)
	perim = sum(l['len'] for l in lines)
	print perim

	#likely to be a card. . .
	if abs(perim - 850) < 100:
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


def watch_for_card(camera):
	has_moved = False

	font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 1.0, 1.0)
	img = cv.QueryFrame(camera)
	size = cv.GetSize(img)
	n_pixels = size[0]*size[1]

	grey = cv.CreateImage(size, 8,1)
	recent_frames = [cv.CloneImage(grey)]
	base = cv.CloneImage(grey)
	cv.CvtColor(img, base, cv.CV_RGB2GRAY)
	cv.ShowImage('card', base)
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

		#if we're stable-ish
		if biggest_diff < 10:
			#print "stable"
			#if we're similar to base, update base
			#else, check for card
			base_diff = max(sum_squared(base, frame) / n_pixels for frame in recent_frames)
			if base_diff < 2:
				base = cv.CloneImage(grey)
				cv.ShowImage('base', base)
				has_moved = False
			elif has_moved:
				corners = detect_card(grey, base)
				if corners is not None:
					card = get_card(img, corners)
					cv.ShowImage('card', card)
					has_moved = False
		else:
			has_moved = True







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

def score(card, known):
	r = cv.CreateMat(1, 1, cv.CV_32FC1)
    cv.MatchTemplate(card, known, r, cv.CV_TM_CCORR)
    return r[0,0]


r = cv.CreateMat(1, 1, cv.CV_32FC1)
'''
