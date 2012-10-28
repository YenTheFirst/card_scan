import cv
import math

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
	#print perim

	#likely to be a card. . .
	#if abs(perim - 1200) < 160:
	if perim > 700:
		#extrapolate the rectangle from the hull.
		#if our 4 longest lines make up 80% of our perimiter
		l = sum(l['len'] for l in lines[0:4])
		#print "l = ",l
		if l / perim  >0.7:
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


