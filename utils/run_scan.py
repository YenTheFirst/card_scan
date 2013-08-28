import cv
import scan_card

from elixir import session, setup_all
import sqlalchemy
from sqlalchemy import func
from models import *
import re

setup_all(True)

cam = cv.CreateCameraCapture(0)
scan_card.setup_windows()

def capture_box(cam, boxnum):
	while True: #retry loop
		retry = False
		captures = scan_card.watch_for_card(cam)
		scan_card.save_captures(boxnum, captures)
		print "captured %d cards. is this correct?" % len(captures)
		answer = raw_input()
		print "got answer: ", answer
		if re.search('[yc]',answer):
			break #finish the function
		else:
			print "try editing captures_%02d to match" % boxnum
			answer = ""
			while not re.match('[cra]', answer):
				print "when done - (c)orrected? (r)etry scan? or (a)bort?"
				answer = raw_input()
			if re.search('c',answer):
				break
			elif re.search('r',answer):
				continue
			elif re.search('a',answer):
				return #abort the scan
			#default will retry

	scan_card.folder_to_db(boxnum)


if __name__ == '__main__':
	#main loop
	while True:
		next_box = session.query(func.max(sqlalchemy.cast(InvCard.box, sqlalchemy.Integer))).first()[0] + 1
		print "scanning %02d" % next_box
		capture_box(cam, next_box)
