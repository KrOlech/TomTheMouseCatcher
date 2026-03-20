import cv2

class MaskOutMazeBorders:

    def __init__(self, corners:dict):
        self.corners = corners
        self.img = cv2.imread(r"C:\Users\Zenbook\PycharmProjects\TomTheMouseCatcher\src\Python\Butch\exampleImage\LHKpqswK.jpg")

    def run(self):
        for key, point in self.corners.items():
            cv2.circle(self.img, point, 10, (0, 0, 0), thickness=-1)
            cv2.putText(self.img, key,(point[0],point[1]+45),1,2,(0, 0, 0), 2)
        cv2.imwrite(r"C:\Users\Zenbook\PycharmProjects\TomTheMouseCatcher\src\Python\Butch\exampleImage\maskOutMazeBorders.jpg", self.img)

        # nessesery linies Horizontal
        '''
        10-20; 30-40, 11-21, 31-41, 32-42, 12-22, 33-43, 13-23

        '''

        for l,m in [("10","20"), ("30","40"), ("11","21"), ("31","41"), ("32","42"), ("12","22"), ("33","43"), ("13","23")]:

            p1, p2 = self.line(self.corners[l], self.corners[m])
            cv2.line(self.img, p1, p2, (0, 0, 0), 2)


        cv2.imwrite(
            r"C:\Users\Zenbook\PycharmProjects\TomTheMouseCatcher\src\Python\Butch\exampleImage\maskOutMazeBorders-Lines.jpg",
            self.img)


    def line(self, point1, point2):
        if (point2[0] - point1[0]) == 0:
            return 0
        a = (point2[1] - point1[1]) / (point2[0] - point1[0])
        b = point1[1] - a * point1[0]
        zp = -b/a
        if (zp < 0):
            print("zp",point1, point2)
        if(b<0):
            print("b",point1, point2, b, zp)
            return (2048, int(a*2048+b)), (int(zp), 0)

        return (0, int(b)), (int(zp),0)
