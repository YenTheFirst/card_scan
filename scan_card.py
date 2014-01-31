"""
copyright 2013-2014 Talin Salway

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import math
import cv
import os
import sqlite3
import numpy
import cv2
from detect_card import detect_card
from cv_utils import float_version, show_scaled, sum_squared, ccoeff_normed
import config

def get_card(color_capture, corners):
	target = [(0,0), (223,0), (223,310), (0,310)]
	mat = cv.CreateMat(3,3, cv.CV_32FC1)
	cv.GetPerspectiveTransform(corners, target, mat)
	warped = cv.CloneImage(color_capture)
	cv.WarpPerspective(color_capture, warped, mat)
	cv.SetImageROI(warped, (0,0,223,310) )
	return warped

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
	#print "update windows!"
	l = len(captures)
	for i in xrange(1,min(n,l)+1):
		#print "setting ",i
		tmp = cv.CloneImage(captures[-i])
		cv.PutText(tmp, "%s" % (l-i+1), (1,24), font, (255,255,255))
		cv.ShowImage("card_%d" % i, tmp)
		cv.SetMouseCallback("card_%d" % i, card_window_clicked, l - i)

def watch_for_card(camera):
	has_moved = False
	been_to_base = False

	global captures
	global font
	captures = []

	font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 1.0, 1.0)
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
		if len(recent_frames) > 3:
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


		#if we're stable-ish
		if biggest_diff < 10:
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
			if base_corr > 0.75 and not been_to_base:
				base = cv.CloneImage(grey)
			#	cv.ShowImage('debug', base)
				has_moved = False
				been_to_base = True
				print "STATE: been to base. waiting for move"
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
					print "STATE: detected. waiting for go to base"
		else:
			if not has_moved:
				print "STATE: has moved. waiting for stable"
			has_moved = True


def setup_windows():
	cv.NamedWindow('card_1')
	cv.NamedWindow('card_2')
	cv.NamedWindow('card_3')
	#cv.NamedWindow('base')
	cv.NamedWindow('win')
	#cv.StartWindowThread()



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

