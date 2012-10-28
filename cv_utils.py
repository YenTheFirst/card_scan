import numpy
import cv
import cv2

def img_from_buffer(buffer):
	np_arr = numpy.fromstring(buffer,'uint8')
	np_mat = cv2.imdecode(np_arr,0)
	return cv.fromarray(np_mat)

def show_scaled(win, img):
	min, max, pt1, pt2 = cv.MinMaxLoc(img)
	cols, rows = cv.GetSize(img)
	tmp = cv.CreateMat(rows, cols,cv.CV_32FC1)
	cv.Scale(img, tmp, 1.0/(max-min), 1.0*(-min)/(max-min))
	cv.ShowImage(win,tmp)

def float_version(img):
	tmp = cv.CreateImage( cv.GetSize(img), 32, 1)
	cv.ConvertScale(img, tmp, 1/255.0)
	return tmp

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

