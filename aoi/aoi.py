"""
This file is part of OpenSesame.

OpenSesame is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenSesame is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with OpenSesame.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import math
import numpy
from PyQt4 import QtCore, QtGui

import openexp.canvas
from openexp.keyboard import keyboard
from libopensesame import item, exceptions
from libqtopensesame import qtplugin
from libqtopensesame.ui import sketchpad_widget_ui

def pos2psychopos(pos, dispsize):

	"""Returns a converted position tuple (x,y) (internal use)
	arguments
	pos		--	a (x,y) position tuple, assuming (0,0) is top left
	dispsize	--	a (width, height) tuple for the display resolution
				
	returns
	pos		--	a (x,y) tuple that makes sense to PsychoPy (i.e. (0,0) is
				display center; bottom left is (-,-) and top right is
				(+,+))
	"""
	
	x = pos[0] - dispsize[0]/2
	y = (pos[1] - dispsize[1]/2) * -1
	
	return (x,y)


def psychopos2pos(pos, dispsize):

	"""Returns a converted position tuple (x,y) (internal use)
	arguments
	pos		--	a (x,y) tuple that makes sense to PsychoPy (i.e. (0,0) is
				display center; bottom left is (-,-) and top right is
				(+,+))
	dispsize	--	a (width, height) tuple for the display resolution

	returns
	pos		--	a (x,y) position tuple, assuming (0,0) is top left
	"""
	
	x = pos[0] + dispsize[0]/2
	y = (pos[1] * -1) + dispsize[1]/2
	
	return (x,y)


class aoi(item.item):
	
	"""A plug-in to apply areas of interest"""
	
	def __init__(self, name, experiment, string=None):

		"""
		Constructor

		Arguments:
		name		--	item name
		experiment	--	an experiment object

		Keyword arguments:
		string		--	a definitional string (default=None)
		"""
		
		self.item_type = u"aoi"
		self.spname = u'welcome'
		self.aoiname = u"AOI_0"
		self.aoidict = {}
		self.aoidictstr = str(self.aoidict)
		self.x = 0
		self.y = 0
		self.w = 200
		self.h = 100
		self.gridsize = 10
		self.description = \
			u"Define areas of interest (AOIs) with a rectangle shape"
		item.item.__init__(self, name, experiment, string)
		
		if hasattr(self.experiment, "aoidict"):
			self.aoidict = self.experiment.aoidict
		else:
			self.aoidict = {}
		self.aoinr = len(self.aoidict)
	
	def prepare(self):

		"""
		Prepare the plug-in

		Returns:
		True
		"""
		
		# check for eyetracker
		if not hasattr(self.experiment, "eyetracker"):
			raise exceptions.runtime_error( \
				u"Please connect to the eyetracker using the the eyetracker_calibrate plugin before using the AOI plugin")
		
		# canvas
		self.cv = openexp.canvas.canvas()
		self.cv.copy(self.experiment.items[self.get(u'spname')].canvas)
		
		# keyboard
		self.kb = keyboard(self.experiment, keylist=None, timeout=1)
		
		# string to dict
		exec("self.aoidict = %s" % self.get("aoidictstr"))
		
		# create numpy arrays (for faster processing)
		blnkarray = numpy.array(numpy.zeros(len(self.aoidict)),dtype=numpy.int)
		self._lx = numpy.array(blnkarray, copy=True) # left x border
		self._rx = numpy.array(blnkarray, copy=True) # right x border
		self._ty = numpy.array(blnkarray, copy=True) # top y border
		self._by = numpy.array(blnkarray, copy=True) # bottom y border
		self._namelist = numpy.array(self.aoidict.keys())
		self._aoicount = numpy.zeros(len(self._namelist))
		self._notaoicount = 0
		
		for aoinr in range(0,len(self._namelist)):
			x, y, w, h = self.aoidict[self._namelist[aoinr]]
			self._lx[aoinr] = x
			self._rx[aoinr] = x + w
			self._ty[aoinr] = y
			self._by[aoinr] = y + h
				
		return True
	
	def run(self):

		"""
		Run the plug-in

		Returns:
		True
		"""
		
		stop = False
		fixating = False
		t0 = self.cv.show()
		
		while not stop:
			
			if not fixating:
				# wait for fixation
				fx, fy = self.experiment.eyetracker.wait_for_fixation_start()
				fixating = True
				
				# check if fixpos is in an AOI
				xina = (self._lx < fx) == (self._rx > fx) # fixation between x borders
				yina = (self._by < fy) == (self._ty > fy) # fixation between y borders
				self._aoicount[xina&yina] += 1 # add one to the count of every fixated AOI
				
				# if no AOI is hit
				if sum(xina&yina) == 0:
					self._notaoicount += 1
			else:
				self.experiment.eyetracker.wait_for_fixation_end()
				fixating = False
			
			# response
			response, t1 = self.kb.get_key()

			# timeout
			if (self.time() - t0 > self.timeout and not self.notimeout) or (response != None):
				stop = True
		
		# handle variables
		for aoi in range(0,len(self._namelist)):
			varname = u'fixcount_' + self._namelist[aoi]
			self.experiment.set(varname,self._aoicount[aoi])
		self.experiment.set(u'fixcount_notAOI', self._notaoicount)
		self.experiment.set(u'response', response)
		self.experiment.set(u'response_time', t1-t0)
		
		return True
		

class qtaoi(aoi, qtplugin.qtplugin):

	"""GUI part of the plug-in"""

	def __init__(self, name, experiment, string=None):

		"""
		Constructor

		Arguments:
		name		--	item name
		experiment	--	an experiment object

		Keyword arguments:
		string		--	a definitional string (default=None)
		"""
		
		aoi.__init__(self, name, experiment, string)
		qtplugin.qtplugin.__init__(self, __file__)
		

	def init_edit_widget(self):

		"""Initialize the controls"""

		self.lock = False
		qtplugin.qtplugin.init_edit_widget(self, False)
		self.add_line_edit_control("spname", "Sketchpad", tooltip= \
			"The name of the sketchpad for which the AOIs apply")
		self.add_line_edit_control("aoiname", "AOI name", tooltip= \
			"The name of the new AOI", default="aoi_%d" % self.aoinr)
		self.add_spinbox_control("x", "X position", 0, 10000, suffix=' px', \
			tooltip= "The horizontal coordinate of the AOI")
		self.add_spinbox_control("y", "Y position", 0, 10000, suffix=' px', \
			tooltip= "The vertical coordinate of the AOI")
		self.add_spinbox_control('w', \
			'width', 0, 2000, suffix=' px', tooltip= \
			'The width of the AOI')
		self.add_spinbox_control('h', \
			'height', 0, 2000, suffix=' px', tooltip= \
			'The height of the AOI')
		
		# add button
		# PyQt4 stuff
		button = QtGui.QPushButton(self.experiment.icon(u'add'), u'Add AOI')
		button.setIconSize(QtCore.QSize(16, 16))
		button.clicked.connect(self.add_aoi)
		hbox = QtGui.QHBoxLayout()
		hbox.setMargin(0)
		hbox.addWidget(button)
		widget = QtGui.QWidget()
		widget.setLayout(hbox)
		# libqtopensesame.items.qtplugin.qtplugin
		self.add_control("", widget, "click button to add new AOI") # label, widget, tooltip: label is empty, since text is on button
		
		# inactive line edit, showing number of AOIs
		self.aoi_nr_display = self.add_line_edit_control("aoinr", "AOI count", \
			tooltip = "The number of AOIs that you have currently defined")
		self.aoi_nr_display.setDisabled(True)
		
		# reset button
		# PyQt4 stuff
		button = QtGui.QPushButton(self.experiment.icon(u'delete'), u'Reset')
		button.setIconSize(QtCore.QSize(16, 16))
		button.clicked.connect(self.clear_aois)
		hbox = QtGui.QHBoxLayout()
		hbox.setMargin(0)
		hbox.addWidget(button)
		widget = QtGui.QWidget()
		widget.setLayout(hbox)
		# libqtopensesame.items.qtplugin.qtplugin
		self.add_control("", widget, "click button to delete all AOI") # label, widget, tooltip: label is empty, since text is on button
		
		# grid size editor
		self.add_spinbox_control('gridsize', \
			'Grid size', 5, 1000, suffix=' px', tooltip= \
			'Grid line interdistance')
		
		# credits
		self.add_text("<br><br><small><b>Copyrights Edwin S. Dalmaijer, 2013. Based on PyGaze toolbox: http://www.fss.uu.nl/psn/pygaze/</b></small>")

		# image showing AOIs (should we present canvas on this?)
		self.scene = QtGui.QGraphicsScene() # QGraphicsScene
		self.view = QtGui.QGraphicsView() # QGraphicsView to show scene
		self.view.setRenderHint(QtGui.QPainter.Antialiasing)
		self.view.setScene(self.scene)
		self.view.setFocusPolicy(QtCore.Qt.NoFocus)

		# AOI image background
		self.bgw, self.bgh = self.experiment.resolution()
		self.bgpen = QtGui.QPen()
		self.bgbrush = QtGui.QBrush()
		self.bgpen.setColor(QtGui.QColor(0))
		self.bgbrush.setColor(QtGui.QColor(0))
		self.bgbrush.setStyle(QtCore.Qt.SolidPattern)
		self.scene.setBackgroundBrush(self.bgbrush)
		# draw sketchpad
		if hasattr(self, u'spname'):
			if self.spname in self.experiment.items:
				self.add_sketchpad(self.experiment.items[self.spname])
		
		# AOI image properties
		self.font = QtGui.QFont("sans", 12, QtGui.QFont.Normal, False) # fontfamily, str; pointsize, int; weight, QFont.Normal/Bold; italic, bool
		self.aoicol = 255 # starts at white
		self.pen = QtGui.QPen()
		self.pen.setWidth(3)
		self.pen.setColor(QtGui.QColor(self.aoicol,self.aoicol,self.aoicol))
		self.gridpen = QtGui.QPen()
		self.gridpen.setWidth(1)
		self.gridpen.setColor(QtGui.QColor(0,255,0))
		self.add_grid(gridsize=self.get(u'gridsize'))
		self.brush = QtGui.QBrush()
		self.brush.setColor(QtGui.QColor(self.aoicol,self.aoicol,self.aoicol))
		self.brush.setStyle(QtCore.Qt.SolidPattern)
		
		# add AOI preview display to layout
		hbox = QtGui.QHBoxLayout()
		hbox.setMargin(0)
		hbox.addWidget(self.view)
		widget = QtGui.QWidget()
		widget.setLayout(hbox)
		self.add_control("", widget, "image of your AOIs")
		
		# pad empty space below controls
		self.add_stretch()
		
		self.lock = True
		
	def add_aoi(self):

		# bookkeeping		
		self.aoidict[self.aoiname] = [self.x, self.y, self.w, self.h]
		self.set("aoinr", len(self.aoidict))
		self.set("aoidictstr", self.aoidict)
		#self.experiment.aoidict = self.aoidict
		
		# gui
		self.update_color()
		self.edit_widget()
	
	def clear_aois(self):
		
		# bookkeeping
		self.aoidict = {}
		self.set("aoinr", len(self.aoidict))
		self.set("aoidictstr", self.aoidict)

		# gui
		self.update_color(clearall=True)
		self.edit_widget()
	
	def update_color(self, clearall=False):
		
		# reset colour
		if clearall:
			self.aoicol = 255

		# update colour
		else:
			# change colour for pen and brush
			self.aoicol -= 25
			if self.aoicol < 25:
				self.aoicol = 255
		
		# apply new colour settings
		self.pen.setColor(QtGui.QColor(self.aoicol,self.aoicol,self.aoicol))
		self.brush.setColor(QtGui.QColor(self.aoicol,self.aoicol,self.aoicol))
	
	def refresh_preview(self):
		
		"""Refresh the AOI preview display"""
		
		# clear scene
		self.scene.clear()
		# draw sketchpad
		if hasattr(self, u'spname'):
			if self.spname in self.experiment.items:
				self.add_sketchpad(self.experiment.items[self.spname])
			else:
				warning = self.scene.addText(u"sketchpad '%s' not found" % self.spname, self.font)
				warning.setDefaultTextColor(QtGui.QColor(255,0,0))
		# draw AOIs
		exec("self.aoidict = %s" % self.get(u'aoidictstr'))
		for aoiname in self.aoidict.keys():
			x, y, w, h = self.aoidict[aoiname]
			self.update_color()
			self.scene.addRect(x,y,w,h,self.pen,self.brush)
			aoilbl = self.scene.addText(aoiname,self.font)
			aoilbl.setDefaultTextColor(QtGui.QColor(0))
			lblrect = aoilbl.boundingRect()
			aoilbl.setPos((x+w/2)-(lblrect.width()/2), (y+h/2)-(lblrect.height()/2))
		# draw grid
		self.add_grid(gridsize=self.get(u'gridsize'))

	def apply_edit_changes(self):

		"""Apply the controls"""

		if not qtplugin.qtplugin.apply_edit_changes(self, False) or self.lock:
			return
		self.experiment.main_window.refresh(self.name)

	def edit_widget(self):

		"""Update the controls"""

		# unlock
		self.lock = True
		# edit
		self.refresh_preview()
		qtplugin.qtplugin.edit_widget(self)
		# lock
		self.lock = False
		return self._edit_widget
	
	def add_grid(self, gridsize=10):
		
		"""Draw a grid over the entire scene"""
		
		# vertical lines
		for l in range(1,self.bgw-1,gridsize):
			line = self.scene.addLine(l, 1, l, self.bgh, self.gridpen)
			line.setOpacity(0.25)
		
		# horizontal lines
		for l in range(1,self.bgh,gridsize):
			line = self.scene.addLine(1, l, self.bgw, l, self.gridpen)
			line.setOpacity(0.25)
	
	# all of the functions below are directly ripped off from the sketchpad widget
	# https://github.com/smathot/OpenSesame/blob/master/libqtopensesame/widgets/sketchpad_widget.py
	
	def add_sketchpad(self, sketchpad):
		
		"""Draw the contents of a sketchpad in the AOI preview"""
		
		self.sketchpad = sketchpad
		
		for item in sketchpad.static_items():
			g = None
			try:
				s = self.sketchpad.item_to_string(item)
				item = self.sketchpad.fix_coordinates(item)
				
				# Set the pen and the brush
				pen = QtGui.QPen()
				pen.setWidth(item["penwidth"])
				pen.setColor(QtGui.QColor(item["color"]))
				brush = QtGui.QBrush()
				if item["fill"] == 1:
					brush.setColor(QtGui.QColor(item["color"]))
					brush.setStyle(QtCore.Qt.SolidPattern)
				
				if item["type"] == "rect":
					g = self.rect(item["x"], item["y"], item["w"], item["h"], \
					pen, brush)
				elif item["type"] == "circle":
					g = self.ellipse(item["x"]-0.5*item["r"], \
					item["y"]-0.5*item["r"], item["r"], item["r"], pen, \
					brush)
				elif item["type"] == "ellipse":
					g = self.ellipse(item["x"], item["y"], item["w"], \
					item["h"], pen, brush)
				elif item["type"] == "fixdot":
					g = self.fixdot(item["x"], item["y"], item["color"])
				elif item["type"] == "arrow":
					g = self.arrow(item["x1"], item["y1"], item["x2"], \
					item["y2"], item["arrow_size"], pen)
				elif item["type"] == "line":
					g = self.line(item["x1"], item["y1"], item["x2"], \
					item["y2"], pen)
				elif item["type"] == "textline":
					g = self.textline(item["text"], item["center"]==1, \
					item["x"], item["y"], item["color"], \
					item["font_family"], item["font_size"], \
					item['font_bold'] == 'yes', item['font_italic'] == 'yes')
				elif item["type"] == "image":
					g = self.image(self.sketchpad.experiment.get_file( \
					item["file"]), item["center"]==1, item["x"], \
					item["y"], item["scale"])
				elif item["type"] == "gabor":
					g = self.gabor(item)
				elif item["type"] == "noise":
					g = self.noise(item)
				else:
					print "Could not find", item["type"]
			except:
				print "Error processing %s" % str(item)

	def rect(self, x, y, w, h, pen, brush):

		"""Draw rectangle"""
		
		return self.scene.addRect(x, y, w, h, pen, brush)

	def ellipse(self, x, y, w, h, pen, brush):
	
		"""Draw ellipse"""
		
		return self.scene.addEllipse(x, y, w, h, pen, brush)
	
	def fixdot(self, x, y, color):
	
		"""Draw fixation dot"""
	
		color = QtGui.QColor(color)
		pen = QtGui.QPen()
		pen.setColor(color)
		brush = QtGui.QBrush()
		brush.setColor(color)
		brush.setStyle(QtCore.Qt.SolidPattern)
		r1 = 8
		r2 = 2
		i = self.scene.addEllipse(x - r1, y - r1, 2*r1, 2*r1, pen, brush)
		brush.setColor(QtGui.QColor(self.sketchpad.get("background", \
		_eval=False)))
		self.scene.addEllipse(x - r2, y - r2, 2*r2, 2*r2, pen, brush)
		return i
	
	def arrow(self, sx, sy, ex, ey, arrow_size, pen):
	
		"""Draw arrow"""
		
		i = self.scene.addLine(sx, sy, ex, ey, pen)
		a = math.atan2(ey - sy, ex - sx)
		_sx = ex + arrow_size * math.cos(a + math.radians(135))
		_sy = ey + arrow_size * math.sin(a + math.radians(135))
		self.scene.addLine(_sx, _sy, ex, ey, pen)
		_sx = ex + arrow_size * math.cos(a + math.radians(225))
		_sy = ey + arrow_size * math.sin(a + math.radians(225))
		self.scene.addLine(_sx, _sy, ex, ey, pen)
		return i
	
	def line(self, x1, y1, x2, y2, pen):
	
		"""Draw line"""
		
		return self.scene.addLine(x1, y1, x2, y2, pen)
	
	def textline(self, text, center, x, y, color, font_family, font_size, \
	font_bold, font_italic):
	
		"""Draw textline"""
		
		if font_family == "serif" and os.name == "nt":
			font_family = "times" # WINDOWS HACK: Windows doesn't recognize serif
		if font_bold:
			weight = QtGui.QFont.Bold
		else:
			weight = QtGui.QFont.Normal
			font = QtGui.QFont(font_family, font_size, weight, font_italic)
			text_item = self.scene.addText(text, font)
			text_item.setDefaultTextColor(QtGui.QColor(color))
		if center:
			r = text_item.boundingRect()
			text_item.setPos(x - 0.5 * r.width(), y - 0.5 * r.height())
		else:
			text_item.setPos(x, y)
		return text_item
	
	def image(self, path, center, x, y, scale):
	
		"""Draw image"""
		
		pixmap = QtGui.QPixmap(path)
		
		if pixmap.isNull():
			# Qt4 cannot handle certain funky bitmaps that PyGame can. So if
			# loading the image directly fails, we fall back to loading the
			# image with PyGame and converting it to a QPixmap.
			import pygame
			im = pygame.image.load(path)
			data = pygame.image.tostring(im, "RGBA")
			size = im.get_size()
			image = QtGui.QImage(data, size[0], size[1], \
			QtGui.QImage.Format_ARGB32)
			pixmap = QtGui.QPixmap.fromImage(image)
		
		w = pixmap.width()*scale
		pixmap = pixmap.scaledToWidth(w)
		_item = self.scene.addPixmap(pixmap)
		if center:
			_item.setPos(x - 0.5 * pixmap.width(), y - 0.5 * pixmap.height())
		else:
			_item.setPos(x, y)
		return _item
	
	def gabor(self, item):
	
		"""Draw gabor patch"""
		
		path = openexp.canvas.gabor_file(item["orient"], item["freq"], \
		item["env"], item["size"], item["stdev"], item["phase"], \
		item["color1"], item["color2"], item["bgmode"])
		pixmap = QtGui.QPixmap(path)
		_item = self.scene.addPixmap(pixmap)
		_item.setPos(item["x"]-0.5*pixmap.width(), \
		item["y"]-0.5*pixmap.height())
		return _item
	
	def noise(self, item):
	
		"""Draw noise patch"""
		
		path = openexp.canvas.noise_file(item["env"], item["size"], \
		item["stdev"], item["color1"], item["color2"], item["bgmode"])
		pixmap = QtGui.QPixmap(path)
		_item = self.scene.addPixmap(pixmap)
		_item.setPos(item["x"]-0.5*pixmap.width(), \
		item["y"]-0.5*pixmap.height())
		return _item