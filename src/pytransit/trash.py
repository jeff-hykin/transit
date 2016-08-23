# Copyright 2015.
#   Michael A. DeJesus, Chaitra Ambadipudi, and  Thomas R. Ioerger.
#
#
#    This file is part of TRANSIT.
#
#    TRANSIT is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License.
#
#
#    TRANSIT is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with TRANSIT.  If not, see <http://www.gnu.org/licenses/>.

try:
    import wx
    hasWx = True
except Exception as e:
    hasWx = False


import view_trash
import draw_trash
from math import *
import os
import ntpath

import traceback


try:
    import Image
    import ImageDraw
    import ImageFont
except ImportError:
    import PIL.Image as Image
    import PIL.ImageDraw as ImageDraw
    import PIL.ImageFont as ImageFont


import pytransit.transit_tools as transit_tools
import pytransit.tnseq_tools as tnseq_tools
import pytransit.norm_tools as norm_tools


def WxBitmapToPilImage( myBitmap ) :
    return WxImageToPilImage( WxBitmapToWxImage( myBitmap ) )

def WxBitmapToWxImage( myBitmap ) :
    return wx.ImageFromBitmap( myBitmap )

#-----

def PilImageToWxBitmap( myPilImage ) :
    return WxImageToWxBitmap( PilImageToWxImage( myPilImage ) )

def PilImageToWxImage( myPilImage ):
    myWxImage = wx.EmptyImage( myPilImage.size[0], myPilImage.size[1] )
    try:
        myWxImage.SetData( myPilImage.convert( 'RGB' ).tostring() )
    except:
        myWxImage.SetData( myPilImage.convert( 'RGB' ).tobytes() )
    return myWxImage

def WxImageToWxBitmap( myWxImage ) :
    return myWxImage.ConvertToBitmap()



def fetch_name(filepath):
    return os.path.splitext(ntpath.basename(filepath))[0]


track_prefix = "[TrackView]"
#inherit from the MainFrame created in wxFowmBuilder and create CalcFrame
class TrashFrame(view_trash.MainFrame):
    #constructor
    def __init__(self,parent, dataset_list=["H37Rv_Sassetti_glycerol.wig"], annotation="H37Rv.prot_table", gene=""):



        self.size = wx.Size( 1500,800 )
        self.start = 1
        self.end = 10000

        #self.orf2data = draw_trash.read_prot_table(annotation)
        #self.hash = draw_trash.hash_prot_genes(annotation)

        self.orf2data = transit_tools.get_gene_info(annotation)
        self.hash = transit_tools.get_pos_hash(annotation)
        
        self.features = []

        #Data to facilitate search
        self.name2id = {}
        for orf,(name, desc, start, end, strand) in self.orf2data.items():
            if name not in self.name2id: self.name2id[name] = []
            self.name2id[name].append(orf)

        self.lowerid2id = dict([(x.lower(), x) for x in self.orf2data.keys()])
        self.labels = [fetch_name(d) for d in dataset_list]
        (self.fulldata, self.position) = tnseq_tools.get_data(dataset_list)

        #Save normalized data
        (self.fulldata_norm, factors) = norm_tools.normalize_data(self.fulldata, method="nzmean")
        print track_prefix, "Normalization factors", factors.flatten()

        #initialize parent class
        view_trash.MainFrame.__init__(self,parent)

        if gene:
            self.searchText.SetValue(gene)
            self.searchFunc(gene)

        self.updateFunc(parent)
        self.Fit()



 
    def updateFunc(self,event):
        try:
            start = int(self.startText.GetValue())
            end = int(self.endText.GetValue())

            min_read = 0
            if self.minText.GetValue():
                min_read = int(self.minText.GetValue())

            max_read = 0
            if self.maxText.GetValue():
                max_read = int(self.maxText.GetValue())


    
            if self.normCheck.GetValue():
                image_pil = draw_trash.draw_canvas(self.fulldata_norm, self.position, self.hash, self.orf2data, labels=self.labels, min_read=min_read, max_read=max_read, start=start, end=end)
            else:
                image_pil = draw_trash.draw_canvas(self.fulldata, self.position, self.hash, self.orf2data, labels=self.labels, min_read=min_read, max_read=max_read, start=start, end=end)

            #image_pil = draw_trash.draw_canvas(start, end, min_read, max_read, self.data, self.hash, self.orf2data)
            #image_wxBit = PilImageToWxBitmap( image_pil )
            image_wxImg = PilImageToWxImage( image_pil )
            #self.m_bitmap1 = wx.StaticBitmap(self, -1, image_wxBit, (0, 0))
            self.m_bitmap1.SetBitmap(wx.BitmapFromImage(image_wxImg))
            #self.m_bitmap1 = image_wxBit
            self.Refresh()
            image_pil = ""

        except Exception, e:
            print track_prefix + '[ERROR]:', e
            traceback.print_exc()
            #put a blank string in text when 'Clear' is clicked




    def leftFunc(self, event):
        start = int(self.startText.GetValue())
        end = int(self.endText.GetValue())
        delta = end-start
        new_start = int(start - delta*0.10)
        new_end = int(end - delta*0.10)

        #new_start = start - 500
        #new_end = end - 500
        
        self.startText.SetValue(str(new_start))
        self.endText.SetValue(str(new_end))
        self.updateFunc(event) 


    def rightFunc(self, event):
        start = int(self.startText.GetValue())
        end = int(self.endText.GetValue())
        delta = end-start
        new_start = int(start + delta*0.10)
        new_end = int(end + delta*0.10)

        #new_start = start + 500
        #new_end = end + 500

        self.startText.SetValue(str(new_start))
        self.endText.SetValue(str(new_end))
        self.updateFunc(event)

    
    def zoomInFunc(self, event):
        start = int(self.startText.GetValue())
        end = int(self.endText.GetValue())
        delta = end-start
        new_start = int(start + delta*0.10)
        new_end = int(end - delta*0.10)

        #new_start = start + 500
        #new_end = end - 500

        self.startText.SetValue(str(new_start))
        self.endText.SetValue(str(new_end))
        self.updateFunc(event)


    def zoomOutFunc(self, event):
        start = int(self.startText.GetValue())
        end = int(self.endText.GetValue())
        delta = end-start
        new_start = int(start - delta*0.10)
        new_end = int(end + delta*0.10)

        #new_start = start - 500
        #new_end = end + 500

        self.startText.SetValue(str(new_start))
        self.endText.SetValue(str(new_end))
        self.updateFunc(event)    


    def resetFunc(self, event):
        self.startText.SetValue("1")
        self.endText.SetValue("10000")
        self.minText.SetValue("0")
        self.maxText.SetValue("150")
        self.updateFunc(event)


    def saveImageFunc(self, event):
        finished_image = self.m_bitmap1.GetBitmap()
        output_path = self.SaveFile(DIR=".", FILE="reads_canvas.png")
        if output_path:
            finished_image.SaveFile(output_path, wx.BITMAP_TYPE_PNG)
        print track_prefix, "Image saved to the following path:", output_path
    

    def addFeatureFunc(self, event):
        pass




    def searchFunc(self, event):

        query = self.searchText.GetValue()

        print track_prefix, "Search query:", query
        #check if query is name:
        genes_match_name = self.name2id.get(query.lower(), [])
        gene_match_orf = self.lowerid2id.get(query.lower(), None)
        gene_match_orf_w_c = self.lowerid2id.get(query.lower()+"c", None)


        print track_prefix, "Genes with matching name:", genes_match_name
        print track_prefix, "Genes with matching IDs:", gene_match_orf
        
        if len(genes_match_name) == 1:      # Check if query is a name
            orf_match = genes_match_name[0]
        elif gene_match_orf:                # Check if query is an orf id
            orf_match = gene_match_orf
        elif gene_match_orf_w_c:            # Check if query is an orf id with missing "c" at end
            orf_match = gene_match_orf_w_c
        else:
            return


        start, end, strand, name = self.orf2data.get(orf_match, [0, 2000, "+", "-"])

        print track_prefix, "Matched data:", start, end, strand, name
       
        try:

            #Set the start and end coords with the new info
            self.startText.SetValue(str(start))
            self.endText.SetValue(str(end))

            #Get min/max read info from text controls
            min_read = int(self.minText.GetValue())
            max_read = int(self.maxText.GetValue())

            if self.normCheck.GetValue():
                image_pil = draw_trash.draw_canvas(self.fulldata_norm, self.hash, self.orf2data, labels=self.labels, min_read=min_read, max_read=max_read, start=start, end=end)
            else:
                image_pil = draw_trash.draw_canvas(self.fulldata, self.hash, self.orf2data, labels=self.labels, min_read=min_read, max_read=max_read, start=start, end=end)


            #image_pil = draw_trash.draw_canvas(start, end, min_read, max_read, self.data, self.hash, self.orf2data)
            #image_wxBit = PilImageToWxBitmap( image_pil )
            image_wxImg = PilImageToWxImage( image_pil )
            #self.m_bitmap1 = wx.StaticBitmap(self, -1, image_wxBit, (0, 0))
            self.m_bitmap1.SetBitmap(wx.BitmapFromImage(image_wxImg))
            #self.m_bitmap1 = image_wxBit
            self.Refresh()
            image_pil = ""

        except Exception, e:
            print track_prefix + '[ERROR]:', e
            traceback.print_exc() 
        


    def SaveFile(self, DIR=".", FILE="", WC=""):
        """
        Create and show the Save FileDialog
        """
        path = ""
        dlg = wx.FileDialog(
            self, message="Save file as ...",
            defaultDir=DIR,
            defaultFile=FILE, wildcard=WC, style=wx.SAVE|wx.OVERWRITE_PROMPT
            )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            #print track_prefix, "You chose the following output filename: %s" % path
        dlg.Destroy()
        return path



#mandatory in wx, create an app, False stands for not deteriction stdin/stdout
#refer manual for details
if __name__ == "__main__":
    app = wx.App(False)
     
    #create an object of CalcFrame
    frame = TrashFrame(None)
    #show the frame
    frame.Show(True)
    #start the applications
    app.MainLoop()


