import math
import cv

def find_longest_contour(contour_seq):
    x = contour_seq
    max_len = 0
    max = None
    while x is not None:
        if cv.ArcLength(x) > max_len:
            max_len = cv.ArcLength(x)
            max = x
        x = x.h_next()
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


def detect_card(grey_image, grey_base, thresh=60):
	diff = cv.CloneImage(grey_image)
	cv.AbsDiff(grey_image, grey_base, diff)
	
	edges = cv.CloneImage(grey_image)
	cv.Canny(diff, edges, thresh, thresh)

	contours = cv.FindContours(edges, cv.CreateMemStorage(0))
	longest, length = find_longest_contour(contours)

	#likely to be a card. . .
	if length > 1000:
		#get the convex hull
		hull = cv.ConvexHull2(longest, cv.CreateMemStorage(0), cv.CV_CLOCKWISE, 1)
		#extrapolate the rectangle from the hull.
		lines = longest_lines(hull)
		perim = sum(l['len'] for l in lines)
		#if our 4 longest lines make up 80% of our perimiter
		if sum(l['len'] for l in lines[0:4]) / perim > 0.8:
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
corners should be close to [blah]


test 2
base = cv.LoadImage("base_03.png", 0)
capture = cv.LoadImage("swamp_03.png", 0)
corners =  scan_card.detect_card(capture, base)
corners should not be none
corners should be close to [blah]
'''
