from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.basictypeaccess.array import ByteArray, ShortArray, FloatArray, LongArray
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType, UnsignedLongType
from net.imglib2.type.numeric.real import FloatType
from java.nio import ByteBuffer, ByteOrder
from java.io import RandomAccessFile
from jarray import zeros
import os, sys
from net.imglib2.img.display.imagej import ImageJFunctions as IL

# The path to the folder with the serial sections,
# each stored as a single raw 8-bit image
folderpath = "/home/albert/lab/TEM/L3/microvolume/17-sections-raw/"

# The dimensions of each serial section
section_width, section_height = 2560, 1225
bytesPerPixel = 1 # 8-bit pixels

# One file per serial section
filepaths = [os.path.join(folderpath, filename)
             for filename in sorted(os.listdir(folderpath))]

# Desired dimensions for reaching chunks of a single section
cell_width, cell_height = 1024, 1024 # one megabyte

# Each Cell is a chunk of a single section, hence 3rd dimension is 1 
cell_dimensions = [cell_width, cell_height, 1]

# Volume dimensions
dimensions = [section_width, section_height, len(filepaths)]

# The grid of the CellImg
grid = CellGrid(dimensions, cell_dimensions)
nX, nY, nZ = grid.getGridDimensions()
cells_per_section = nX * nY


def createAccess(bytes, bytesPerPixel):
  """ Return a new access instance for the appropriate pixel type.
      Supports byte, short, float and long. """
  if 1 == bytesPerPixel: # BYTE
    return ByteArray(bytes)
  # Transform bytes into another type
  bb = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN)
  if 2 == bytesPerPixel: # SHORT
    pixels = zeros(len(bytes) / 2, 's')
    bb.asShortBuffer().get(pixels)
    return ShortArray(pixels)
  if 4 == bytesPerPixel: # FLOAT
    pixels = zeros(len(bytes) / 4, 'f')
    bb.asFloatBuffer().get(pixels)
    return FloatArray(pixels)
  if 8 == bytesPerPixel: # LONG
    pixels = zeros(len(bytes) / 8, 'l')
    bb.asLongBuffer().get(pixels)
    return LongArray(pixels)


def createType(bytesPerPixel):
  if 1:
    return UnsignedByteType()
  if 2:
    return UnsignedShortType()
  if 4:
    return FloatType()
  if 8:
    return UnsignedLongType()


# A class to load each Cell
class SectionGet(LazyCellImg.Get):
  def get(self, index):
    ra = None
    try:
      # Read cell origin and dimensions for cell at index
      cellMin  = zeros(3, 'l') # long, 3 dimensions
      cellDims = zeros(3, 'i') # integer, 3 dimensions
      grid.getCellDimensions(index, cellMin, cellDims)
      # Unpack Cell origin (in pixel coordinates)
      x, y, z = cellMin
      # Unpack Cell dimensions: at margins, may be smaller than cell_width, cell_height
      width, height, _ = cellDims # ignore depth: it's 1
      # Read cell from file into a byte array
      ra = RandomAccessFile(filepaths[ z ], 'r')
      read_width = width * bytesPerPixel
      bytes = zeros(read_width * height, 'b')
      # Initial offset to the Cell origin
      offset = (section_width * y + x) * bytesPerPixel
      n_read = 0
      n_pixels = width * height
      # Read line by line
      while n_read < n_pixels:
        ra.seek(offset)
        ra.read(bytes, n_read, read_width)
        n_read += read_width
        offset += section_width * bytesPerPixel
      # Create a new Cell of the right pixel type
      return Cell(cellDims, cellMin, createAccess(bytes, bytesPerPixel))
    except:
      print sys.exc_info()
    finally:
      if ra:
        ra.close() 
  
lazyImg = LazyCellImg(grid, createType(bytesPerPixel), SectionGet())
IL.wrap(lazyImg, "sections").show()

# Extremely slow: each cell is loaded for each pixel read!
# Took 20 seconds to read one single section.
