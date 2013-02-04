import os
import sqlite3
from cv_utils import ccoeff_normed, img_from_buffer, float_version
import cv
import math

PREV, NEXT, KEY, RESULT = 0, 1, 2, 3
MAXSIZE = 3000
class GradientCache:
	def __init__(self, base_dir):
		self.base_dir = base_dir
		self.cache = {}
		self.root = []
		self.root[:] = [self.root, self.root, None, None]
		self.full = False
		self.currsize = 0


	def getCard(self, set_name, name):
		key = "%s/%s" % (set_name, name)
		if key in self.cache:
			#print 'hit', key
			#bump entry to front of list, then return
			link = self.cache[key]
			#remove it from where it is
			link_prev, link_next, key, result = link
			link_prev[NEXT] = link_next
			link_next[PREV] = link_prev
			#put in right before root
			last = self.root[PREV]
			last[NEXT] = self.root[PREV] = link
			link[PREV] = last
			link[NEXT] = self.root
			return result

		#load the image
		path = os.path.join(self.base_dir, set_name, name+".full.jpg")
		img = cv.LoadImage(path.encode('utf-8'),0)
		if cv.GetSize(img) != (223, 310):
			tmp = cv.CreateImage((223, 310), 8, 1)
			cv.Resize(img,tmp)
			img = tmp
		result = gradient(img)[1]

		#print 'miss' , key, self.full
		if self.full:
			#add as the new root
			self.root[KEY] = key
			self.root[RESULT] = result
			self.cache[key] = self.root

			#make the oldelst link the new root
			self.root = self.root[NEXT]
			del self.cache[self.root[KEY]]
			self.root[KEY] = self.root[RESULT] = None
		else:
			# put result in a new link at the front of the queue
			last = self.root[PREV]
			link = [last, self.root, key, result]
			self.cache[key] = last[NEXT] = self.root[PREV] = link
			self.currsize += 1
			self.full = (self.currsize == MAXSIZE)

		return result


def load_sets(base_dir, set_names):
	cards = []
	for dir, subdirs, fnames in os.walk(base_dir):
		set = os.path.split(dir)[1]
		if set in set_names:
			for fname in fnames:
				path = os.path.join(dir, fname)

				img = cv.LoadImage(path.encode('utf-8'),0)
				if cv.GetSize(img) != (223, 310):
					tmp = cv.CreateImage((223, 310), 8, 1)
					cv.Resize(img,tmp)
					img = tmp
				phash = dct_hash(img)
				
				cards.append((
					fname.replace('.full.jpg',''),
					set,
					phash
				))

	return cards

def match_db_cards(known):
	connection = sqlite3.connect("inventory.sqlite3")
	try:
		cursor = connection.cursor()
		cursor.execute("select rowid, scan_png from inv_cards where recognition_status is 'scanned'")
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
				update_c.execute("update inv_cards set name=?, set_name=?, recognition_status=? where rowid=?", [card, set, 'candidate_match', id])
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
	#h = angle_hist(grad)
	#limited_set = sorted([(cv.CompareHist(h, hist, cv.CV_COMP_CORREL), name, set, g) for name,set,g,hist in known_set], reverse=True)[0:1000]
	#h_score, name, set, img = max(limited_set,
	#	key = lambda (h_score, name, set, known): score(grad, known, cv.CV_TM_CCOEFF)
	#)
	phash = dct_hash(card)
	name, set, phash2 = min(known_set,
		key = lambda (n, s, h): hamming_dist(h, phash)
	)
	return (name, set)


def dct_hash(img):
	img = float_version(img)
	small_img = cv.CreateImage((32, 32), 32, 1)
	cv.Resize(img[20:190, 20:205], small_img)

	dct = cv.CreateMat(32, 32, cv.CV_32FC1)
	cv.DCT(small_img, dct, cv.CV_DXT_FORWARD)
	dct = dct[1:9, 1:9]

	avg = cv.Avg(dct)[0]
	dct_bit = cv.CreateImage((8,8),8,1)
	cv.CmpS(dct, avg, dct_bit, cv.CV_CMP_GT)

	return [dct_bit[y, x]==255.0
			for y in xrange(8)
			for x in xrange(8)]

def hamming_dist(h1,h2):
	return sum(b1 != b2 for (b1,b2) in zip(h1,h2))

LIKELY_SETS = [
	'DKA', 'ISD',
	'NPH', 'MBS', 'SOM',
	'ROE', 'WWK', 'ZEN',
	'ARB', 'CON', 'ALA',
	'EVE', 'SHM', 'MOR', 'LRW',
	'M12', 'M11', 'M10', '10E',
	'HOP',
]

