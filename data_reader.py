import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import shapefile
import constants
from geo.drawer import plot, plotPoints, show, showPoints
from geo.shapes import Point, Polygon, Triangle
from point_location.kirkpatrick import Locator
from point_location.point_locator import PointLocator, PointLocatorPoly
from tqdm import tqdm

def ccw(A, B, C):
    """Tests whether the line formed by A, B, and C is ccw"""
    return (B.x - A.x) * (C.y - A.y) < (B.y - A.y) * (C.x - A.x)

class PathFinder:
    def __init__(self):
        pass

    def find_path_funnel(self, point_dict , edge_path, p, q):

        tail = [p]
        left = []
        right = []

        last_edge_l = None
        last_edge_r = None

        for i,e in enumerate(edge_path):
            p1, p2 = point_dict[e[0]], point_dict[e[1]]


            if p2 == last_edge_l or p1 == last_edge_r or (last_edge_r is None and last_edge_l is None and ccw(tail[-1], p2, p1)):
                p1, p2 = p2, p1


            if len(left) == 0 and p1 != tail[-1]: #or (left[-1] == tail[-1]):
                # If appex is the same as previous left, then add the current point
                print("L:reset left")
                left = [p1]
            elif len(left) > 0 and left[-1] != p1:

                if not ccw(tail[-1], p1, left[-1]):

                    last_collision = -1
                    for i,p in enumerate(right):
                        if ccw(tail[-1], p, p1):
                            # Point of right segment is left of point of left segment(violation).
                            # So, add violating vertices to tail
                            tail.append(right[i])
                            last_collision = i

                    if last_collision >= 0:
                        print("L:collision")
                        left = [p1]
                        right = right[last_collision + 1:]
                    else:
                        print("L:narrowing funnel")
                        left[-1] = p1
                else:
                    print("L: appending")
                    left.append(p1)


            if len(right) == 0 and p2 != tail[-1]:
                # If appex is the same as previous right, then add the current point
                right = [p2]
                print("R:reset right")
            elif len(right) > 0 and right[-1] != p2:

                if not ccw(tail[-1], right[-1], p2):

                    last_collision = -1
                    for i,p in enumerate(left):
                        if ccw(tail[-1], p2, p):
                            # Point of right segment is left of point of left segment(violation)
                            # So, add violating vertices to tail
                            tail.append(left[i])
                            last_collision = i

                    if last_collision >= 0:
                        right = [p2]
                        left = left[last_collision + 1:]
                        print("R:collision")
                    else:
                        right[-1] = p2
                        print("R:narrowing funnel")
                else:
                    print("R: appending")
                    right.append(p2)


            last_edge_l = p1
            last_edge_r = p2

        apex = tail[-1]
        # Fix last collisions
        for i, p in enumerate(right):
            if ccw(apex, p, q):
                tail.append(right[i])

        for i,p in enumerate(left):
            if ccw(apex, q, p):
                tail.append(left[i])
        tail.append(q)
        return tail



class ClickEvent():
    def __init__(self, fig, func, button=1):
        self.fig = fig
        self.ax=fig.axes[0]
        self.func=func
        self.button=button
        self.press=False
        self.move = False


    def onclick(self,event):
        if event.inaxes == self.fig.axes[0]:
            if event.button == self.button:
                self.func(event)
    def onpress(self,event):
        self.press=True
    def onmove(self,event):
        if self.press:
            self.move=True
    def onrelease(self,event):
        if self.press and not self.move:
            self.onclick(event)
        self.press=False; self.move=False




class ProgramDriver:

    def __init__(self, shape_file="./data/h/GSHHS_h_L1.shp"):

        self.point_locator = PointLocator()
        self.path_finder = PathFinder()

        # Contain (polygon_id,triangle_id) of the starting
        # and finishing points
        self.s,self.f = None,None

        # Contain the actual starting and finishing point
        self.ps,self.pf = None,None


        with shapefile.Reader(shape_file) as shp:
            shapes = shp.shapes()

        self.polygons = [shape.points for shape in reversed(shapes[:constants.MAX_POLYGONS])]

        print("Processing map")
        for i,p in enumerate(tqdm(self.polygons)):

            self.point_locator.add_polygon(PointLocatorPoly(p))

        print("Map processing finished!")

    def click_event(self,event):

        #print('button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
        #      (event.button, event.x, event.y, event.xdata, event.ydata))

        p = Point(event.xdata,event.ydata)
        l = self.point_locator.locate(p)


        if l is None:
            print('Point not inside any polygon. Pick another one')
            return
        else:
            #self.ps,self.pf = Point(34.45,28.32),Point(35.74,28.9); self.s,self.f = self.point_locator.locate(self.ps),self.point_locator.locate(self.pf)
            if self.s is None:
                self.s = l
                self.ps = p
            elif self.f is None:
                if l[0] != self.s[0]:
                    print('Points not inside the same polygon. Pick another one')
                    return
                else:
                    self.pf = p
                    self.f = l

            if self.s is not None and self.f is not None:
                print('Calculate path: ')
                edge_path = self.point_locator.find_edge_path(self.s[0],self.s[1],self.f[1])

                poly_points = self.point_locator.polygons[self.s[0]].points
                path = self.path_finder.find_path_funnel(poly_points,edge_path,self.ps,self.pf)
                print(path)
                plotPoints(path,'r--')
                self.s,self.f = None,None
                self.ps, self.pf = None, None

        plt.plot(event.xdata, event.ydata,markerfacecolor="red", marker=".", markersize=20)
        self.fig.canvas.draw()


    def show_map(self):

        self.fig = plt.figure()
        print("Rendering matplotlib GUI...")
        polys_to_plot = self.point_locator.polygons
        plot(polys_to_plot)

        ce = ClickEvent(self.fig, self.click_event, button=1)

        self.fig.canvas.mpl_connect('button_press_event', ce.onpress)
        self.fig.canvas.mpl_connect('button_release_event', ce.onrelease)
        self.fig.canvas.mpl_connect('motion_notify_event', ce.onmove)

        #cid = self.fig.canvas.mpl_connect('button_press_event', self.click_event)
        plt.show()


driver = ProgramDriver()
driver.show_map()


