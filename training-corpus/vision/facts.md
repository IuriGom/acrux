# Vision: Key Facts, Concepts, and APIs

This file collects practical facts, syntax, standard-library essentials, common APIs, and language/tool fundamentals for working with images and computer vision in Python.

---

## 1. What Is a Digital Image?

A digital image is a 2-D (or 2-D + channels) array of pixels. In Python, the most common representation is a NumPy `ndarray`.

- **Grayscale image**: shape `(H, W)`, one intensity value per pixel.
- **Color image**: shape `(H, W, C)`, typically `C = 3` (RGB/BGR) or `C = 4` (RGBA/BGRA).
- **Pixel value ranges**:
  - `uint8`: `0` to `255` (most common for storage and display).
  - `uint16`: `0` to `65535` (medical, raw camera data).
  - `float32`/`float64`: often `0.0..1.0` for image processing or `-1..1` / mean-normalized for deep learning.

The origin `(0, 0)` is the top-left pixel. The row index is the `y` coordinate, the column index is the `x` coordinate.

```python
import numpy as np

# A blank 480x640 grayscale image
gray = np.zeros((480, 640), dtype=np.uint8)

# A blank 480x640 RGB image
rgb = np.zeros((480, 640, 3), dtype=np.uint8)

print(gray.shape)  # (480, 640)
print(rgb.shape)   # (480, 640, 3)
```

---

## 2. Essential Libraries

### 2.1 Pillow (PIL Fork)

Pillow is the friendly fork of PIL. It is the standard high-level image manipulation library in Python.

```bash
pip install Pillow
```

```python
from PIL import Image

# Open an image (lazy operation)
im = Image.open("photo.jpg")

# Key attributes
print(im.format)   # 'JPEG'
print(im.size)     # (width, height)
print(im.mode)     # 'RGB', 'RGBA', 'L', 'P', 'CMYK', etc.

# Force load into memory
im.load()

# Save
im.save("copy.png")
```

**Important modes**:

| Mode | Meaning |
|------|---------|
| `1`  | 1-bit black and white |
| `L`  | 8-bit grayscale |
| `P`  | 8-bit palette-mapped |
| `RGB`| 3x8-bit true color |
| `RGBA`| 3x8-bit true color + alpha |
| `CMYK`| 4x8-bit subtractive color |
| `LAB`| 3x8-bit CIE L*a*b* |
| `HSV`| 3x8-bit Hue/Saturation/Value |

Pillow loads images lazily. The file handle stays open until the image is loaded or the object is closed. Prefer the context-manager form:

```python
with Image.open("photo.jpg") as im:
    im.load()
    # work with im
```

### 2.2 OpenCV

OpenCV is the dominant library for real-time computer vision and classical image processing.

```bash
# Base package
pip install opencv-python

# Includes extra (SIFT, SURF disabled in modern builds for patent reasons, but contrib extras)
pip install opencv-contrib-python
```

```python
import cv2

img = cv2.imread("photo.jpg")           # Default: BGR, 8-bit
gray = cv2.imread("photo.jpg", cv2.IMREAD_GRAYSCALE)
unchanged = cv2.imread("photo.jpg", cv2.IMREAD_UNCHANGED)

cv2.imshow("window", img)
cv2.waitKey(0)
cv2.destroyAllWindows()

cv2.imwrite("output.png", img)
```

**Critical fact**: OpenCV reads and writes color images in **BGR** order by default. Matplotlib, Pillow, and most deep-learning frameworks expect **RGB**.

### 2.3 NumPy

NumPy is the universal substrate. OpenCV images are NumPy arrays; Pillow images convert to/from NumPy arrays with `np.asarray()` and `Image.fromarray()`.

```python
import numpy as np
from PIL import Image

im = Image.open("photo.jpg")
arr = np.asarray(im)          # PIL -> NumPy (RGB order)
back = Image.fromarray(arr)    # NumPy -> PIL
```

### 2.4 scikit-image

scikit-image is a scientific image-processing library built on NumPy/SciPy.

```bash
pip install scikit-image
```

```python
from skimage import io, filters, color, morphology, transform
img = io.imread("photo.jpg")        # RGB order
gray = color.rgb2gray(img)          # float64 in [0, 1]
edges = filters.sobel(gray)
```

### 2.5 imageio

imageio is a clean, unified I/O library for images, video, and scientific formats.

```bash
pip install imageio
```

```python
import imageio.v3 as iio
img = iio.imread("photo.jpg")       # Returns NumPy array, RGB order by default
iio.imwrite("output.png", img)
```

### 2.6 matplotlib

matplotlib is used for visualization.

```python
import matplotlib.pyplot as plt

plt.imshow(img)        # Expects RGB or grayscale
plt.axis("off")
plt.show()
```

### 2.7 torchvision

torchvision provides datasets, transforms, and pretrained models for PyTorch computer vision.

```python
from torchvision import transforms, models

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),                    # PIL -> tensor [0, 1]
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])
```

---

## 3. Color Spaces and Conversions

### 3.1 RGB vs. BGR

- **RGB**: red-green-blue, order `[R, G, B]`. Used by Pillow, matplotlib, scikit-image, web, most ML frameworks.
- **BGR**: blue-green-red, order `[B, G, R]`. Used by OpenCV historically.

Convert between them:

```python
import cv2

# OpenCV BGR -> RGB
img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

# RGB -> BGR
img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
```

```python
import numpy as np

# Fast channel-swap with NumPy
img_rgb = img_bgr[..., ::-1]
img_bgr = img_rgb[..., ::-1]
```

### 3.2 Grayscale Conversion

OpenCV uses the ITU-R BT.601 luma coefficients on BGR data:

```
Y = 0.114 * B + 0.587 * G + 0.299 * R
```

```python
gray_cv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
gray_pil = im.convert("L")   # Pillow uses the same coefficients for RGB
```

scikit-image returns a float64 image in `[0, 1]`:

```python
from skimage import color
gray = color.rgb2gray(img_rgb)   # float64, range [0, 1]
```

### 3.3 HSV / HSL / LAB

- **HSV**: Hue (0-179 in OpenCV, 0-360 elsewhere), Saturation, Value. Useful for color-based segmentation.
- **LAB**: L* (lightness), a* (green-red), b* (blue-yellow). Perceptually uniform.
- **YCrCb**: Used in JPEG compression and video.

```python
hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
```

In OpenCV, Hue is scaled to `0..179` for 8-bit images (factor of 2 from standard `0..360`).

### 3.4 Alpha Compositing

An alpha channel represents opacity. `255` = fully opaque, `0` = fully transparent.

```python
from PIL import Image

fg = Image.open("foreground.png").convert("RGBA")
bg = Image.open("background.jpg").convert("RGBA")

# Paste foreground onto background using its alpha channel
bg.paste(fg, (0, 0), fg)
```

---

## 4. Loading and Saving Images

### 4.1 Pillow

```python
from PIL import Image
import io

# From file
with Image.open("input.jpg") as im:
    im.load()

# From bytes
with open("input.jpg", "rb") as f:
    data = f.read()
im = Image.open(io.BytesIO(data))

# To bytes
buf = io.BytesIO()
im.save(buf, format="PNG")
bytes_data = buf.getvalue()
```

### 4.2 OpenCV

```python
import cv2

# Flags
img = cv2.imread("input.jpg", cv2.IMREAD_COLOR)        # default, BGR
gray = cv2.imread("input.jpg", cv2.IMREAD_GRAYSCALE)
unchanged = cv2.imread("input.jpg", cv2.IMREAD_UNCHANGED)
any_depth = cv2.imread("input.jpg", cv2.IMREAD_ANYDEPTH)
any_color = cv2.imread("input.jpg", cv2.IMREAD_ANYCOLOR)

# Save with quality
cv2.imwrite("output.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
cv2.imwrite("output.png", img, [cv2.IMWRITE_PNG_COMPRESSION, 6])
```

OpenCV cannot read/write some formats without codecs (e.g., WebP may require the appropriate plugin). Always check for `None`:

```python
img = cv2.imread("input.jpg")
if img is None:
    raise FileNotFoundError("Could not load input.jpg")
```

### 4.3 imageio

```python
import imageio.v3 as iio

img = iio.imread("input.jpg")
iio.imwrite("output.png", img)

# Read metadata
meta = iio.immeta("input.jpg")
```

### 4.4 scikit-image

```python
from skimage import io
img = io.imread("input.jpg")       # RGB
io.imsave("output.png", img)
```

---

## 5. Image Properties and Metadata

### 5.1 Dimensions and Data Type

```python
import cv2
img = cv2.imread("photo.jpg")
height, width = img.shape[:2]
channels = img.shape[2] if img.ndim == 3 else 1
dtype = img.dtype
```

### 5.2 EXIF Data

EXIF (Exchangeable Image File Format) stores camera settings, orientation, GPS, timestamps.

```python
from PIL import Image
from PIL.ExifTags import TAGS

with Image.open("photo.jpg") as im:
    exif = im.getexif()
    for tag_id, value in exif.items():
        tag = TAGS.get(tag_id, tag_id)
        print(f"{tag}: {value}")
```

Common EXIF tags:

| Tag | Meaning |
|-----|---------|
| `Orientation` | 1=normal, 3=180°, 6=90° CW, 8=90° CCW |
| `Make`, `Model` | Camera info |
| `DateTime` | Capture timestamp |
| `FNumber`, `ExposureTime`, `ISOSpeedRatings` | Exposure settings |
| `GPSInfo` | GPS coordinates |

**Orientation handling** is critical. Many mobile photos are stored as 8 MP but tagged with rotation. Use Pillow's `ImageOps.exif_transpose()`:

```python
from PIL import ImageOps
with Image.open("photo.jpg") as im:
    im = ImageOps.exif_transpose(im)
```

### 5.3 ICC Color Profiles

Images can embed ICC profiles that describe color spaces (sRGB, Adobe RGB, etc.). Pillow preserves profiles in `im.info['icc_profile']`. Converting color spaces requires `PIL.ImageCms` or third-party libraries like `colour-science`.

---

## 6. Pixel Access and Array Manipulation

### 6.1 NumPy Indexing

```python
import cv2
import numpy as np

img = cv2.imread("photo.jpg")

# Access a pixel (B,G,R) tuple
b, g, r = img[100, 200]

# Set a region to red (BGR)
img[50:150, 100:200] = (0, 0, 255)

# Copy a region
roi = img[50:150, 100:200].copy()

# Access a channel
red_channel = img[:, :, 2]
```

### 6.2 Pillow Pixel Access

```python
from PIL import Image

im = Image.open("photo.jpg")
print(im.getpixel((200, 100)))   # (R, G, B)
im.putpixel((200, 100), (255, 0, 0))

# Faster pixel-level work: load into a PixelAccess object
px = im.load()
print(px[200, 100])
px[200, 100] = (255, 0, 0)
```

### 6.3 Masking

```python
import numpy as np

# Boolean mask from a condition
mask = img[:, :, 2] > 200   # red channel > 200
img[mask] = [0, 255, 0]     # set those pixels to green
```

---

## 7. Geometric Transformations

### 7.1 Resizing

**Pillow**:

```python
from PIL import Image

im = Image.open("photo.jpg")
im_resized = im.resize((300, 200), Image.Resampling.LANCZOS)

# Thumbnail (preserves aspect ratio, modifies in place)
im.thumbnail((300, 300), Image.Resampling.LANCZOS)
```

**OpenCV**:

```python
import cv2

resized = cv2.resize(img, (300, 200), interpolation=cv2.INTER_LINEAR)

# Scale factors
resized = cv2.resize(img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
```

Interpolation flags in OpenCV:

| Flag | Best for |
|------|----------|
| `INTER_NEAREST` | nearest neighbor; fast, blocky |
| `INTER_LINEAR` | default; bilinear, good for upscaling/downscaling |
| `INTER_CUBIC` | bicubic; slower, sharper |
| `INTER_LANCZOS4` | Lanczos; high quality, slow |
| `INTER_AREA` | area resampling; best for downscaling |

Size ordering:
- OpenCV: `(width, height)`
- NumPy shape: `(height, width, channels)`
- Pillow: `(width, height)`
- PyTorch tensors: `(C, H, W)`

### 7.2 Cropping

```python
from PIL import Image
im = Image.open("photo.jpg")
cropped = im.crop((left, upper, right, lower))
```

```python
import cv2
cropped = img[y1:y2, x1:x2]
```

### 7.3 Rotation and Flipping

**Pillow**:

```python
im_rotated = im.rotate(45, expand=True, resample=Image.Resampling.BICUBIC)
im_flipped = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
```

**OpenCV**:

```python
(h, w) = img.shape[:2]
center = (w // 2, h // 2)
M = cv2.getRotationMatrix2D(center, 45, 1.0)
rotated = cv2.warpAffine(img, M, (w, h))

# Flip
flipped = cv2.flip(img, 1)   # 1=horizontal, 0=vertical, -1=both
```

### 7.4 Affine and Perspective Transforms

**Affine transform** (preserves parallel lines):

```python
import cv2
import numpy as np

pts1 = np.float32([[50, 50], [200, 50], [50, 200]])
pts2 = np.float32([[10, 100], [200, 50], [100, 250]])
M = cv2.getAffineTransform(pts1, pts2)
affine = cv2.warpAffine(img, M, (cols, rows))
```

**Perspective transform** (four-point mapping, e.g., document scanning):

```python
pts1 = np.float32([[56, 65], [368, 52], [28, 387], [389, 390]])
pts2 = np.float32([[0, 0], [300, 0], [0, 300], [300, 300]])
M = cv2.getPerspectiveTransform(pts1, pts2)
dst = cv2.warpPerspective(img, M, (300, 300))
```

---

## 8. Image Filtering and Convolution

### 8.1 Blurring

```python
import cv2

blur = cv2.blur(img, (5, 5))                          # average
gaussian = cv2.GaussianBlur(img, (5, 5), 0)           # Gaussian
median = cv2.medianBlur(img, 5)                       # median, good for salt-and-pepper
bilateral = cv2.bilateralFilter(img, 9, 75, 75)       # edge-preserving
```

Kernel sizes must be positive and odd (except for `bilateralFilter`, where diameter is used).

### 8.2 Sharpening

A simple sharpening kernel:

```python
import numpy as np
import cv2

kernel = np.array([[0, -1, 0],
                   [-1, 5, -1],
                   [0, -1, 0]])
sharpened = cv2.filter2D(img, -1, kernel)
```

### 8.3 Edge Detection

**Sobel** (gradient-based):

```python
sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
magnitude = cv2.magnitude(sobelx, sobely)
```

**Laplacian**:

```python
laplacian = cv2.Laplacian(gray, cv2.CV_64F)
```

**Canny**:

```python
edges = cv2.Canny(gray, threshold1=100, threshold2=200)
```

Canny steps:
1. Gaussian blur for noise reduction.
2. Compute gradient magnitude and direction (Sobel).
3. Non-maximum suppression to thin edges.
4. Hysteresis thresholding with two thresholds.

Rule of thumb: `threshold2 = 2 * threshold1` or `3 * threshold1`.

### 8.4 Custom Kernels

```python
kernel = np.ones((3, 3), np.float32) / 9
smoothed = cv2.filter2D(img, -1, kernel)
```

---

## 9. Thresholding and Morphology

### 9.1 Thresholding

```python
import cv2

# Binary threshold
_, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

# Adaptive threshold (handles uneven lighting)
adaptive = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY, 11, 2
)

# Otsu's automatic threshold
_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
```

Threshold types:

| Type | Behavior |
|------|----------|
| `THRESH_BINARY` | `dst(x) = maxval if src(x) > thresh else 0` |
| `THRESH_BINARY_INV` | inverted |
| `THRESH_TRUNC` | `dst(x) = thresh if src(x) > thresh else src(x)` |
| `THRESH_TOZERO` | `dst(x) = src(x) if src(x) > thresh else 0` |
| `THRESH_TOZERO_INV` | inverted |

### 9.2 Morphological Operations

```python
import cv2
import numpy as np

kernel = np.ones((5, 5), np.uint8)

eroded = cv2.erode(binary, kernel, iterations=1)
dilated = cv2.dilate(binary, kernel, iterations=1)
opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)     # erosion + dilation (removes noise)
closing = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)    # dilation + erosion (fills holes)
gradient = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel)
```

Morphological operations work on binary or grayscale images. The structuring element (`kernel`) defines the neighborhood.

---

## 10. Histograms and Contrast

### 10.1 Histograms

```python
import cv2
import matplotlib.pyplot as plt

hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
plt.plot(hist)
plt.xlim([0, 256])
plt.show()
```

### 10.2 Histogram Equalization

```python
equalized = cv2.equalizeHist(gray)
```

**CLAHE** (Contrast Limited Adaptive Histogram Equalization) is better for local contrast:

```python
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
cl_img = clahe.apply(gray)
```

### 10.3 Contrast Stretching

```python
import numpy as np

p2, p98 = np.percentile(gray, (2, 98))
scaled = np.clip((gray - p2) / (p98 - p2) * 255, 0, 255).astype(np.uint8)
```

---

## 11. Contours and Shape Analysis

### 11.1 Finding Contours

```python
import cv2

contours, hierarchy = cv2.findContours(
    binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
)

# Draw contours
cv2.drawContours(img, contours, -1, (0, 255, 0), 2)
```

Retrieval modes:

| Mode | Meaning |
|------|---------|
| `RETR_EXTERNAL` | only outer contours |
| `RETR_LIST` | all contours, no hierarchy |
| `RETR_TREE` | all contours with full hierarchy |
| `RETR_CCOMP` | two-level hierarchy (outer and holes) |

Approximation methods:

| Method | Meaning |
|--------|---------|
| `CHAIN_APPROX_NONE` | store all points |
| `CHAIN_APPROX_SIMPLE` | compress horizontal/vertical/diagonal segments |
| `CHAIN_APPROX_TC89_L1`, `TC89_KCOS` | Teh-Chin chain approx |

### 11.2 Contour Features

```python
for cnt in contours:
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    x, y, w, h = cv2.boundingRect(cnt)
    rect = cv2.minAreaRect(cnt)            # rotated bounding box
    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
    
    # Shape approximation
    epsilon = 0.02 * perimeter
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    
    # Convex hull
    hull = cv2.convexHull(cnt)
    
    # Moments and centroid
    M = cv2.moments(cnt)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
```

### 11.3 Shape Matching

```python
# Compare two contours
score = cv2.matchShapes(contour1, contour2, cv2.CONTOURS_MATCH_I1, 0.0)
# Lower score = more similar
```

---

## 12. Feature Detection and Description

### 12.1 Harris Corners

```python
corners = cv2.cornerHarris(np.float32(gray), 2, 3, 0.04)
```

### 12.2 Shi-Tomasi Good Features to Track

```python
corners = cv2.goodFeaturesToTrack(gray, maxCorners=100, qualityLevel=0.01, minDistance=10)
```

### 12.3 ORB

ORB is a free alternative to SIFT/SURF.

```python
orb = cv2.ORB_create(nfeatures=500)
kp, des = orb.detectAndCompute(gray, None)
img_kp = cv2.drawKeypoints(img, kp, None, color=(0, 255, 0))
```

### 12.4 SIFT

SIFT is available in `opencv-contrib-python`.

```python
sift = cv2.SIFT_create()
kp, des = sift.detectAndCompute(gray, None)
```

### 12.5 Feature Matching

```python
# BFMatcher
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
matches = bf.match(des1, des2)
matches = sorted(matches, key=lambda x: x.distance)

# FLANN (for SIFT/SURF)
FLANN_INDEX_KDTREE = 1
index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
search_params = dict(checks=50)
flann = cv2.FlannBasedMatcher(index_params, search_params)
matches = flann.knnMatch(des1, des2, k=2)
```

---

## 13. Video Processing

### 13.1 Reading Video

```python
import cv2

cap = cv2.VideoCapture("video.mp4")
if not cap.isOpened():
    raise IOError("Cannot open video")

fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

while True:
    ret, frame = cap.read()
    if not ret:
        break
    # process frame
    cv2.imshow("frame", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### 13.2 Writing Video

```python
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter("output.mp4", fourcc, 20.0, (width, height))

while True:
    ret, frame = cap.read()
    if not ret:
        break
    out.write(frame)

out.release()
```

Common FourCC codes:

| Code | Codec |
|------|-------|
| `mp4v` | MPEG-4 |
| `avc1`, `H264` | H.264 (may require OpenCV built with FFmpeg) |
| `XVID` | MPEG-4 Part 2 |
| `MJPG` | Motion JPEG |

### 13.3 Webcam Capture

```python
cap = cv2.VideoCapture(0)   # device index 0
ret, frame = cap.read()
cap.release()
```

---

## 14. Image Formats and Compression

### 14.1 Lossy vs. Lossless

| Format | Compression | Alpha | Notes |
|--------|-------------|-------|-------|
| JPEG | Lossy | No | Photos, small file size, artifacts at low quality |
| PNG | Lossless | Yes | Graphics, screenshots, larger than JPEG for photos |
| WebP | Lossy/lossless | Yes | Modern replacement for JPEG/PNG |
| TIFF | Lossy/lossless/None | Yes | High bit depth, scientific/medical |
| BMP | None | No | Uncompressed, large |
| GIF | Lossless (256 colors) | Binary | Animations |
| HEIC/HEIF | Lossy/lossless | Yes | Modern mobile format |

### 14.2 JPEG Quality

```python
from PIL import Image
im.save("output.jpg", quality=85, optimize=True, progressive=True)
```

JPEG is lossy. Repeatedly opening and saving JPEG degrades quality.

### 14.3 PNG Compression Levels

```python
im.save("output.png", compress_level=6)   # 0=none, 9=max
```

---

## 15. NumPy Recipes for Images

### 15.1 Creating Standard Test Images

```python
import numpy as np

# Grayscale gradient
gradient = np.tile(np.arange(256, dtype=np.uint8), (256, 1))

# Color checkerboard
checker = np.zeros((256, 256, 3), dtype=np.uint8)
checker[::2, ::2] = [255, 255, 255]
checker[1::2, 1::2] = [255, 255, 255]

# Random noise
noise = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
```

### 15.2 Type Conversions

```python
# uint8 -> float32 [0, 1]
float_img = img.astype(np.float32) / 255.0

# float32 [0, 1] -> uint8
uint8_img = np.clip(float_img * 255, 0, 255).astype(np.uint8)

# Use skimage utilities
from skimage import img_as_float, img_as_ubyte
f = img_as_float(img)
u = img_as_ubyte(f)
```

### 15.3 Channel Manipulation

```python
# Split channels (OpenCV BGR)
b, g, r = cv2.split(img)
merged = cv2.merge([b, g, r])

# Swap red and blue
img_rb_swapped = img[:, :, [2, 1, 0]]

# Add alpha channel
alpha = np.full((h, w), 255, dtype=np.uint8)
rgba = np.dstack([img, alpha])
```

---

## 16. Visualization

### 16.1 matplotlib

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(10, 5))
axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
axes[0].set_title("Image")
axes[1].imshow(edges, cmap="gray")
axes[1].set_title("Edges")
plt.show()
```

### 16.2 OpenCV Windows

```python
cv2.imshow("Image", img)
key = cv2.waitKey(0) & 0xFF
if key == ord('s'):
    cv2.imwrite("saved.png", img)
cv2.destroyAllWindows()
```

`cv2.waitKey(1)` is required inside video loops to allow event processing. On some platforms, `imshow` without `waitKey` may not display.

---

## 17. Pillow Advanced APIs

### 17.1 ImageFilter

```python
from PIL import Image, ImageFilter

blurred = im.filter(ImageFilter.GaussianBlur(radius=2))
sharpened = im.filter(ImageFilter.SHARPEN)
edges = im.filter(ImageFilter.FIND_EDGES)
embossed = im.filter(ImageFilter.EMBOSS)
contour = im.filter(ImageFilter.CONTOUR)
```

### 17.2 ImageEnhance

```python
from PIL import ImageEnhance

bright = ImageEnhance.Brightness(im).enhance(1.5)
contrast = ImageEnhance.Contrast(im).enhance(1.5)
color = ImageEnhance.Color(im).enhance(1.5)
sharp = ImageEnhance.Sharpness(im).enhance(2.0)
```

### 17.3 ImageOps

```python
from PIL import ImageOps

grey = ImageOps.grayscale(im)
inverted = ImageOps.invert(im)
auto_contrast = ImageOps.autocontrast(im)
equalized = ImageOps.equalize(im)
flipped = ImageOps.flip(im)            # vertical
mirrored = ImageOps.mirror(im)         # horizontal
exif_fixed = ImageOps.exif_transpose(im)
```

### 17.4 Drawing

```python
from PIL import Image, ImageDraw, ImageFont

draw = ImageDraw.Draw(im)
draw.rectangle([10, 10, 100, 100], outline="red", width=3)
draw.text((10, 120), "Hello", fill="white")
```

---

## 18. OpenCV Advanced APIs

### 18.1 Template Matching

```python
import cv2

result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
```

Methods:

| Method | Best result |
|--------|-------------|
| `TM_SQDIFF` | minimum value |
| `TM_SQDIFF_NORMED` | minimum value |
| `TM_CCORR` | maximum value |
| `TM_CCORR_NORMED` | maximum value |
| `TM_CCOEFF` | maximum value |
| `TM_CCOEFF_NORMED` | maximum value |

### 18.2 Hough Line Transform

```python
edges = cv2.Canny(gray, 50, 150)
lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180,
                        threshold=100, minLineLength=50, maxLineGap=10)
```

### 18.3 Hough Circle Transform

```python
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                           param1=50, param2=30, minRadius=0, maxRadius=0)
```

### 18.4 Watershed Segmentation

```python
# markers: sure background=1, unknown=0, foreground=2..
markers = cv2.watershed(img, markers)
img[markers == -1] = [0, 0, 255]   # boundary
```

### 18.5 GrabCut

```python
mask = np.zeros(img.shape[:2], np.uint8)
bgdModel = np.zeros((1, 65), np.float64)
fgdModel = np.zeros((1, 65), np.float64)
rect = (50, 50, 450, 290)
cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
foreground = img * mask2[:, :, np.newaxis]
```

---

## 19. Deep Learning Preprocessing

### 19.1 ImageNet Normalization

Pretrained PyTorch vision models expect:

- Input tensor shape: `(N, 3, H, W)`
- dtype: `torch.float32`
- Range: normalized with mean `[0.485, 0.456, 0.406]` and std `[0.229, 0.224, 0.225]`

```python
import torch
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])
```

### 19.2 Bounding Box Formats

| Format | Meaning | Example |
|--------|---------|---------|
| `xyxy` | (x1, y1, x2, y2) | `(10, 20, 50, 80)` |
| `xywh` | (x1, y1, width, height) | `(10, 20, 40, 60)` |
| `cxcywh` | (center_x, center_y, width, height) | `(30, 50, 40, 60)` |

Conversions:

```python
def xyxy_to_xywh(box):
    x1, y1, x2, y2 = box
    return [x1, y1, x2 - x1, y2 - y1]

def xywh_to_cxcywh(box):
    x, y, w, h = box
    return [x + w/2, y + h/2, w, h]
```

### 19.3 Data Augmentation

Common augmentations:

```python
from torchvision.transforms import v2

transform = v2.Compose([
    v2.RandomResizedCrop(224, scale=(0.08, 1.0)),
    v2.RandomHorizontalFlip(p=0.5),
    v2.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    v2.ToImage(),
    v2.ToDtype(torch.float32, scale=True),
    v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
```

Augmentations should usually be applied only to training data, not validation/test data.

---

## 20. Camera Geometry Basics

### 20.1 Pinhole Camera Model

A 3-D point `X = (X, Y, Z)` projects to image point `x = (u, v)`:

```
u = fx * X/Z + cx
v = fy * Y/Z + cy
```

Camera matrix:

```
K = [[fx,  0, cx],
     [ 0, fy, cy],
     [ 0,  0,  1]]
```

### 20.2 Distortion

Radial distortion coefficients `k1, k2, k3` and tangential `p1, p2` model lens distortion. OpenCV's `calibrateCamera` estimates them.

### 20.3 Undistort

```python
mapx, mapy = cv2.initUndistortRectifyMap(K, dist, None, K, (w, h), cv2.CV_32FC1)
undistorted = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR)
```

---

## 21. Common File Operations

### 21.1 Listing Image Files

```python
from pathlib import Path

image_paths = list(Path("images").glob("**/*.jpg"))
image_paths.extend(Path("images").glob("**/*.png"))
```

### 21.2 Reading Many Images Efficiently

Use a generator or list comprehension:

```python
from PIL import Image

images = [Image.open(p) for p in image_paths]
```

For very large datasets, prefer lazy loading or data loaders.

### 21.3 Verifying Image Integrity

```python
from PIL import Image

def is_valid_image(path):
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False
```

`im.verify()` does not load pixel data; it checks file structure.

---

## 22. Security and Safety

### 22.1 Decompression Bombs

Pillow limits the number of pixels via `Image.MAX_IMAGE_PIXELS` to prevent ZIP/GIF/PNG decompression bombs. Raising the limit or disabling it exposes the process to OOM attacks.

```python
from PIL import Image
Image.MAX_IMAGE_PIXELS = None   # DANGEROUS: disables protection
```

OpenCV has no equivalent built-in limit; validate image dimensions after loading.

### 22.2 Untrusted Inputs

- Never trust filenames or EXIF data from untrusted sources.
- Validate image dimensions before processing.
- Run image decoding in sandboxed or resource-limited environments when possible.
- Be cautious with `Image.show()` / `cv2.imshow()` in server code.

---

## 23. Performance Facts

- **Avoid loops over pixels** in Python. Vectorized NumPy/OpenCV operations are orders of magnitude faster.
- **OpenCV** is generally faster than Pillow for low-level operations on large arrays.
- **Pillow** is convenient for high-level transformations and format handling.
- **scikit-image** is higher-level and often slower but more readable for research.
- **Memory layout**: OpenCV uses BGR, H-W-C contiguous arrays. PyTorch expects C-H-W.
- **Resizing**: use `INTER_AREA` for downscaling, `INTER_CUBIC`/`INTER_LANCZOS4` for upscaling.
- **Batching**: deep-learning preprocessing benefits from batching and GPU transfer.

---

## 24. Quick Reference Tables

### 24.1 OpenCV Imread Flags

| Flag | Value | Behavior |
|------|-------|----------|
| `IMREAD_UNCHANGED` | -1 | as-is, including alpha |
| `IMREAD_GRAYSCALE` | 0 | grayscale |
| `IMREAD_COLOR` | 1 | BGR color (default) |
| `IMREAD_ANYDEPTH` | 2 | 16-bit/32-bit when available |
| `IMREAD_ANYCOLOR` | 4 | color in any available format |

### 24.2 Pillow Resampling Filters

| Filter | Quality/Speed |
|--------|---------------|
| `NEAREST` | fastest, lowest quality |
| `BOX` | good for downscaling |
| `BILINEAR` | default, good balance |
| `HAMMING` | sharper than bilinear |
| `BICUBIC` | sharper, slower |
| `LANCZOS` | highest quality, slowest |

### 24.3 Color Conversion Constants

| Conversion | Use |
|------------|-----|
| `COLOR_BGR2RGB` | OpenCV to matplotlib/PIL |
| `COLOR_BGR2GRAY` | OpenCV grayscale |
| `COLOR_BGR2HSV` | color segmentation |
| `COLOR_BGR2LAB` | perceptual color work |
| `COLOR_RGB2BGR` | PIL to OpenCV |
| `COLOR_GRAY2BGR` | grayscale to 3-channel BGR |

---

## 25. Glossary

- **Pixel**: smallest addressable element of an image.
- **Channel**: a single color/intensity component (e.g., R, G, B).
- **Color space**: a coordinate system for representing colors (RGB, HSV, LAB).
- **Histogram**: distribution of pixel intensities.
- **Kernel / structuring element**: small matrix used for convolution or morphology.
- **Convolution**: sliding a kernel over an image to compute output pixels.
- **Morphology**: shape-based operations on binary/grayscale images.
- **Feature descriptor**: a vector describing a local image region (ORB, SIFT).
- **Homography**: a 3x3 transformation mapping points between two planes.
- **FourCC**: four-character code identifying a video codec.
- **EXIF**: metadata embedded in image files.
- **Alpha channel**: transparency channel.
- **Lossy compression**: irreversible compression (JPEG).
- **Lossless compression**: reversible compression (PNG).


## 26. Additional Core Libraries

### 26.1 Albumentations

Albumentations is a fast, flexible image augmentation library widely used for deep learning.

```bash
pip install albumentations
```

```python
import albumentations as A
from albumentations.pytorch import ToTensorV2

transform = A.Compose([
    A.RandomResizedCrop(height=224, width=224, scale=(0.08, 1.0)),
    A.HorizontalFlip(p=0.5),
    A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=15, p=0.5),
    A.RGBShift(r_shift_limit=15, g_shift_limit=15, b_shift_limit=15, p=0.5),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

augmented = transform(image=img_rgb)["image"]
```

Albumentations works with NumPy arrays in RGB order and is generally faster than torchvision for the same augmentations because it uses optimized OpenCV backends.

### 26.2 imgaug

imgaug is another heavy-duty augmentation library. It is powerful but has a steeper API and is less actively maintained than Albumentations.

```python
import imgaug.augmenters as iaa

seq = iaa.Sequential([
    iaa.Fliplr(0.5),
    iaa.Affine(rotate=(-15, 15)),
    iaa.GaussianBlur(sigma=(0, 1.0)),
])
```

### 26.3 Kornia

Kornia provides differentiable computer vision operations for PyTorch.

```bash
pip install kornia
```

```python
import kornia
import torch

x = torch.rand(2, 3, 224, 224)
gray = kornia.color.rgb_to_grayscale(x)
sobel = kornia.filters.sobel(gray)
```

### 26.4 timm (PyTorch Image Models)

timm provides pretrained models, data loading utilities, and augmentation recipes.

```bash
pip install timm
```

```python
import timm

model = timm.create_model("resnet50.a1_in1k", pretrained=True)
```

### 26.5 OpenCV DNN Module

OpenCV includes a deep-learning inference module that can run ONNX, Caffe, TensorFlow, and PyTorch-exported models without requiring the full frameworks.

```python
net = cv2.dnn.readNetFromONNX("model.onnx")
blob = cv2.dnn.blobFromImage(img, scalefactor=1/255.0, size=(224, 224),
                              mean=(0, 0, 0), swapRB=True, crop=False)
net.setInput(blob)
out = net.forward()
```

---

## 27. Image Segmentation Basics

Image segmentation partitions an image into meaningful regions.

### 27.1 Semantic vs. Instance Segmentation

- **Semantic segmentation**: every pixel gets a class label; no object distinction.
- **Instance segmentation**: every pixel gets a class label and each object instance is separated.
- **Panoptic segmentation**: combines semantic and instance segmentation.

### 27.2 Threshold-Based Segmentation

```python
_, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
segmented = cv2.bitwise_and(img, img, mask=mask)
```

### 27.3 Color-Based Segmentation

```python
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lower = np.array([35, 50, 50])
upper = np.array([85, 255, 255])
mask = cv2.inRange(hsv, lower, upper)
```

### 27.4 Watershed

Watershed treats pixel intensities as a topographic surface and floods basins from markers.

```python
# Distance transform to find sure foreground
import cv2
import numpy as np

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Noise removal
kernel = np.ones((3, 3), np.uint8)
opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

# Sure background
sure_bg = cv2.dilate(opening, kernel, iterations=3)

# Sure foreground via distance transform
dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
_, sure_fg = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)

# Unknown region
sure_fg = np.uint8(sure_fg)
unknown = cv2.subtract(sure_bg, sure_fg)

# Markers
_, markers = cv2.connectedComponents(sure_fg)
markers = markers + 1
markers[unknown == 255] = 0

markers = cv2.watershed(img, markers)
img[markers == -1] = [255, 0, 0]
```

### 27.5 scikit-image Segmentation

```python
from skimage import segmentation, color, filters

edges = filters.sobel(gray)
seg = segmentation.watershed(edges, markers=100)
seg_color = color.label2rgb(seg, image=img_rgb, bg_label=0)
```

---

## 28. Object Detection Basics

### 28.1 Classical Detectors

**Haar Cascades** (legacy but lightweight):

```python
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

for (x, y, w, h) in faces:
    cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
```

**HOG + SVM** (via scikit-image or OpenCV):

```python
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
rects, weights = hog.detectMultiScale(img, winStride=(4, 4), padding=(8, 8), scale=1.05)
```

### 28.2 Modern Deep Detectors

Common families:

- **YOLO**: single-shot, fast, anchor-based or anchor-free.
- **SSD**: single-shot with multi-scale feature maps.
- **Faster R-CNN**: two-stage, high accuracy.
- **DETR**: transformer-based, set-prediction.

Most deep detectors output bounding boxes plus class scores. Post-processing includes:

1. Confidence thresholding.
2. Non-maximum suppression (NMS) to remove overlapping boxes.

### 28.3 Non-Maximum Suppression

```python
def nms(boxes, scores, threshold):
    """Simple greedy NMS for xyxy boxes."""
    indices = np.argsort(scores)[::-1]
    keep = []
    while len(indices) > 0:
        current = indices[0]
        keep.append(current)
        if len(indices) == 1:
            break
        current_box = boxes[current]
        rest = boxes[indices[1:]]
        iou = compute_iou(current_box, rest)
        indices = indices[1:][iou <= threshold]
    return keep
```

OpenCV provides `cv2.dnn.NMSBoxes`.

---

## 29. Optical Character Recognition (OCR)

### 29.1 pytesseract

Tesseract is an open-source OCR engine. The Python wrapper is `pytesseract`.

```bash
pip install pytesseract
# Also install the tesseract binary separately
```

```python
import pytesseract
from PIL import Image

text = pytesseract.image_to_string(Image.open("scan.png"), lang="eng")
data = pytesseract.image_to_data(Image.open("scan.png"), output_type=pytesseract.Output.DICT)
```

Preprocessing improves OCR:

1. Convert to grayscale.
2. Resize to 300 DPI equivalent.
3. Apply thresholding or denoising.
4. Deskew if necessary.

### 29.2 EasyOCR

EasyOCR is a deep-learning OCR library.

```bash
pip install easyocr
```

```python
import easyocr
reader = easyocr.Reader(["en"])
result = reader.readtext("sign.jpg")
for (bbox, text, conf) in result:
    print(text, conf)
```

---

## 30. Image Similarity and Quality Metrics

### 30.1 Mean Squared Error (MSE)

```python
import numpy as np

def mse(a, b):
    return np.mean((a.astype(float) - b.astype(float)) ** 2)
```

### 30.2 Peak Signal-to-Noise Ratio (PSNR)

```python
def psnr(a, b, max_val=255.0):
    m = mse(a, b)
    if m == 0:
        return float('inf')
    return 20 * np.log10(max_val / np.sqrt(m))
```

scikit-image:

```python
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

psnr_val = peak_signal_noise_ratio(ref, img, data_range=255)
ssim_val = structural_similarity(ref, img, data_range=255, channel_axis=2)
```

### 30.3 Histogram Comparison

```python
hist1 = cv2.calcHist([img1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
hist2 = cv2.calcHist([img2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

# Methods: CORREL, CHISQR, INTERSECT, BHATTACHARYYA, HELLINGER
correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
```

---

## 31. Fourier and Frequency Analysis

### 31.1 2-D Discrete Fourier Transform

```python
import numpy as np
import cv2

dft = cv2.dft(np.float32(gray), flags=cv2.DFT_COMPLEX_OUTPUT)
dft_shift = np.fft.fftshift(dft)

magnitude = 20 * np.log(cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1]) + 1)

# Inverse
ishift = np.fft.ifftshift(dft_shift)
img_back = cv2.idft(ishift)
img_back = cv2.magnitude(img_back[:, :, 0], img_back[:, :, 1])
```

### 31.2 NumPy FFT

```python
import numpy as np

F = np.fft.fft2(gray)
Fshift = np.fft.fftshift(F)
magnitude = np.log(np.abs(Fshift) + 1)

ifft = np.fft.ifft2(np.fft.ifftshift(Fshift))
reconstructed = np.abs(ifft)
```

### 31.3 High-Pass / Low-Pass Filters

A low-pass filter in frequency domain removes high-frequency noise/edges. A high-pass filter enhances edges.

```python
rows, cols = gray.shape
crow, ccol = rows // 2, cols // 2

mask = np.zeros((rows, cols, 2), np.uint8)
mask[crow-30:crow+30, ccol-30:ccol+30] = 1

fshift = dft_shift * mask
```

---

## 32. Pyramids and Multi-Scale Processing

### 32.1 Gaussian Pyramid

```python
# Downsample
g_down = cv2.pyrDown(img)

# Upsample
g_up = cv2.pyrUp(img)
```

### 32.2 Laplacian Pyramid

A Laplacian pyramid stores the difference between a level and the upsampled version of the next level. It is used for image blending.

```python
layer = img.copy()
pyramid = []

for _ in range(6):
    gp = cv2.pyrDown(layer)
    lap = cv2.subtract(layer, cv2.pyrUp(gp))
    pyramid.append(lap)
    layer = gp
```

---

## 33. Image Blending and Compositing

### 33.1 Simple Alpha Blending

```python
import cv2

blended = cv2.addWeighted(img1, 0.5, img2, 0.5, 0)
```

### 33.2 Feathered Blending

Create a smooth transition between two images using a weight mask.

```python
mask = np.linspace(0, 1, width).astype(np.float32)
mask = np.tile(mask, (height, 1))

blended = (img1.astype(float) * mask[..., None] +
           img2.astype(float) * (1 - mask[..., None]))
blended = blended.astype(np.uint8)
```

### 33.3 Seamless Cloning

OpenCV's seamless cloning blends a region from one image into another while preserving gradients.

```python
center = (img.shape[1] // 2, img.shape[0] // 2)
normal = cv2.seamlessClone(obj, background, mask, center, cv2.NORMAL_CLONE)
mixed = cv2.seamlessClone(obj, background, mask, center, cv2.MIXED_CLONE)
```

---

## 34. Image Augmentation Details

### 34.1 Geometry

- Flip (horizontal, vertical).
- Rotation (90-degree multiples or arbitrary).
- Scale and crop (random resized crop).
- Affine transforms (shear, translation).
- Perspective distortion.
- Elastic deformation.

### 34.2 Photometric

- Brightness, contrast, saturation, hue shifts.
- Gamma correction.
- Gaussian noise, salt-and-pepper noise.
- Blur, sharpening.
- Color jitter.

### 34.3 Mixing Augmentations

- **MixUp**: blends two images and labels.
- **CutMix**: cuts a patch from one image and pastes into another.
- **Cutout / Random Erasing**: masks random rectangular regions.

---

## 35. Dataset and DataLoader Patterns

### 35.1 PyTorch Dataset

```python
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image
import os

class ImageFolder(Dataset):
    def __init__(self, root, transform=None):
        self.paths = [os.path.join(root, f) for f in os.listdir(root)]
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img
```

### 35.2 TFDS / TensorFlow

```python
import tensorflow_datasets as tfds

dataset = tfds.load("cats_vs_dogs", split="train", as_supervised=True)
```

### 35.3 Streaming Large Datasets

For datasets that do not fit in memory, load samples lazily in `__getitem__` and use a `DataLoader` with multiple workers.

---

## 36. NumPy Advanced Recipes for Images

### 36.1 Padding

```python
import numpy as np

# Constant padding
padded = np.pad(img, ((10, 10), (20, 20), (0, 0)), mode='constant', constant_values=0)

# Edge padding
padded = np.pad(img, ((10, 10), (20, 20), (0, 0)), mode='edge')
```

### 36.2 Tiling / Mosaics

```python
def tile_images(images, cols):
    rows = (len(images) + cols - 1) // cols
    h, w = images[0].shape[:2]
    canvas = np.zeros((h * rows, w * cols, 3), dtype=np.uint8)
    for i, img in enumerate(images):
        r, c = divmod(i, cols)
        canvas[r*h:(r+1)*h, c*w:(c+1)*w] = img
    return canvas
```

### 36.3 Random Cropping

```python
def random_crop(img, crop_h, crop_w):
    h, w = img.shape[:2]
    top = np.random.randint(0, h - crop_h + 1)
    left = np.random.randint(0, w - crop_w + 1)
    return img[top:top+crop_h, left:left+crop_w]
```

### 36.4 Normalization with NumPy

```python
mean = np.array([0.485, 0.456, 0.406])
std = np.array([0.229, 0.224, 0.225])
normalized = (img.astype(float) / 255.0 - mean) / std
```

---

## 37. Parallel and Batch Processing

### 37.1 Multiprocessing for Image Resizing

```python
from multiprocessing import Pool
from PIL import Image
import os

def resize_one(path):
    try:
        with Image.open(path) as im:
            im.thumbnail((512, 512))
            im.save(os.path.join("out", os.path.basename(path)))
        return True
    except Exception:
        return False

with Pool(processes=4) as pool:
    results = pool.map(resize_one, image_paths)
```

### 37.2 Joblib

```python
from joblib import Parallel, delayed

Parallel(n_jobs=4)(delayed(resize_one)(p) for p in image_paths)
```

### 37.3 Batch Loading with DataLoader

```python
from torch.utils.data import DataLoader

loader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=4, pin_memory=True)
```

---

## 38. Image Streaming and Generators

For video or large image sequences, process frames one at a time instead of loading everything.

```python
def frame_generator(path):
    cap = cv2.VideoCapture(path)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        yield frame
    cap.release()

for frame in frame_generator("video.mp4"):
    process(frame)
```

---

## 39. Handling Special Image Types

### 39.1 TIFF and Multi-Page Images

```python
from PIL import Image

with Image.open("stack.tif") as im:
    for i in range(im.n_frames):
        im.seek(i)
        im.save(f"frame_{i}.png")
```

### 39.2 GIF Animation

```python
from PIL import Image

frames = []
for path in frame_paths:
    frames.append(Image.open(path))

frames[0].save("animation.gif", save_all=True, append_images=frames[1:],
               duration=100, loop=0)
```

### 39.3 RAW / DNG Camera Files

RAW files require specialized libraries such as `rawpy` (LibRaw bindings) or `imageio`.

```python
import rawpy

with rawpy.imread("photo.dng") as raw:
    rgb = raw.postprocess()
```

### 39.4 Medical Images (DICOM)

Use `pydicom` or `SimpleITK`.

```python
import pydicom

ds = pydicom.dcmread("scan.dcm")
img = ds.pixel_array
```

---

## 40. Working with Transparency

### 40.1 Splitting and Recomposing RGBA

```python
from PIL import Image

im = Image.open("rgba.png")
r, g, b, a = im.split()

# Composite over white
bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
composite = Image.alpha_composite(bg, im).convert("RGB")
```

### 40.2 Removing the Alpha Channel

```python
# Drop alpha
rgb = im.convert("RGB")

# Or premultiply then drop
rgba = im.convert("RGBA")
premultiplied = Image.alpha_composite(Image.new("RGBA", im.size, (0,0,0,0)), rgba)
rgb = premultiplied.convert("RGB")
```

### 40.3 Alpha Blending Two NumPy Arrays

```python
import numpy as np

def blend_rgba(foreground, background, alpha):
    alpha = alpha[:, :, None] / 255.0
    return (foreground * alpha + background * (1 - alpha)).astype(np.uint8)
```

---

## 41. Text and Annotations

### 41.1 OpenCV Text

```python
cv2.putText(img, "label", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
            1.0, (0, 255, 0), 2, cv2.LINE_AA)
```

### 41.2 Pillow Text with Custom Font

```python
from PIL import Image, ImageDraw, ImageFont

draw = ImageDraw.Draw(im)
try:
    font = ImageFont.truetype("arial.ttf", 24)
except OSError:
    font = ImageFont.load_default()

draw.text((10, 10), "Hello", fill=(255, 255, 255), font=font)
```

### 41.3 Bounding Box Annotations

```python
import cv2

def draw_box(img, box, label, color=(0, 255, 0)):
    x1, y1, x2, y2 = box
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.putText(img, label, (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
```

---

## 42. Image I/O Performance Notes

- `PIL.Image.open` is lazy; pixel data is loaded on first access.
- `cv2.imread` is eager and returns a NumPy array.
- For repeated decoding, consider `imageio` or pre-decoding to a memory-mapped format.
- Use `np.load` / `np.save` for intermediate NumPy caches.
- For huge images, consider tile-based reading (TIF, JPEG2000) or `cv2.imreadmulti`.

---

## 43. Coordinate Systems and Conventions

| Library | Image shape | Point order | Color order |
|---------|-------------|-------------|-------------|
| NumPy | `(H, W, C)` | `(row, col)` | user-defined |
| OpenCV | `(H, W, C)` | `(x, y)` for points | BGR |
| Pillow | `(width, height)` | `(x, y)` | RGB |
| matplotlib | `(H, W, C)` | `(x, y)` axes | RGB |
| PyTorch tensor | `(C, H, W)` | — | RGB |
| TensorFlow tensor | `(H, W, C)` or `(B, H, W, C)` | — | RGB |

---

## 44. Handling EXIF Orientation Correctly

Mobile cameras often store images physically rotated and rely on EXIF `Orientation` to indicate correct display. Failure to handle this is a common source of "sideways" images.

```python
from PIL import Image, ImageOps

def load_image_correct(path):
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        return im
```

OpenCV does not apply EXIF orientation automatically. If you need it, read orientation from EXIF and rotate accordingly, or load via Pillow and convert.

---

## 45. Gamma and Linear Color

Most stored images are gamma-encoded (non-linear). For physically correct blending, resizing, or lighting computations, convert to linear light first.

```python
import numpy as np

def to_linear(img, gamma=2.2):
    return np.power(img.astype(float) / 255.0, gamma)

def from_linear(img, gamma=2.2):
    return np.clip(np.power(img, 1.0 / gamma) * 255, 0, 255).astype(np.uint8)
```

Pillow and OpenCV operate on gamma-encoded values by default.

---

## 46. Image Resizing Deep Dive

### 46.1 Choosing an Interpolation

- **Downscaling**: `INTER_AREA` usually gives the cleanest results; it applies pixel-area relation.
- **Upscaling**: `INTER_CUBIC` or `INTER_LANCZOS4` are sharper than bilinear.
- **Nearest neighbor**: fastest; useful for pixel art or label masks where interpolation would change class IDs.
- **Label masks**: always use nearest-neighbor to avoid introducing new class indices.

### 46.2 Aspect Ratio

Always preserve aspect ratio unless the task explicitly requires a fixed distorted shape. Use letterboxing or cropping.

```python
def resize_keep_aspect(img, target_size):
    h, w = img.shape[:2]
    scale = min(target_size / h, target_size / w)
    new_h, new_w = int(h * scale), int(w * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
```

---

## 47. Validation and Debugging

### 47.1 Inspect an Image Quickly

```python
print(img.shape, img.dtype, img.min(), img.max())
```

### 47.2 Check for NaN or Inf

```python
assert not np.isnan(img).any()
assert not np.isinf(img).any()
```

### 47.3 Visualize Channels

```python
fig, axs = plt.subplots(1, 3, figsize=(12, 4))
for i, (ax, title) in enumerate(zip(axs, ["R", "G", "B"])):
    ax.imshow(img[:, :, i], cmap="gray")
    ax.set_title(title)
plt.show()
```

### 47.4 Save Intermediate Results

When debugging pipelines, save each stage to disk.

```python
stages = [("gray", gray), ("blurred", blurred), ("edges", edges)]
for name, stage in stages:
    cv2.imwrite(f"debug_{name}.png", stage)
```

---

## 48. Environment Setup

### 48.1 Typical Requirements

```text
opencv-python
opencv-contrib-python
Pillow
numpy
matplotlib
scikit-image
imageio
albumentations
pytorch torchvision torchaudio
```

### 48.2 Verify Installations

```python
import cv2, PIL, numpy, skimage, matplotlib, torchvision
print(cv2.__version__)
print(PIL.__version__)
print(numpy.__version__)
print(skimage.__version__)
```

### 48.3 Headless OpenCV

On servers without displays, install the headless variant:

```bash
pip install opencv-python-headless
```

Do not install both `opencv-python` and `opencv-python-headless` in the same environment.

---

## 49. Cross-Library Conversion Cheatsheet

### 49.1 OpenCV -> Pillow

```python
from PIL import Image
pil_img = Image.fromarray(cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB))
```

### 49.2 Pillow -> OpenCV

```python
import cv2
bgr_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
```

### 49.3 OpenCV -> PyTorch Tensor

```python
import torch

rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
```

### 49.4 PyTorch Tensor -> OpenCV

```python
import torch

rgb = tensor.permute(1, 2, 0).numpy()
bgr = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
```

### 49.5 Pillow -> PyTorch Tensor

```python
from torchvision import transforms
tensor = transforms.ToTensor()(pil_img)   # C,H,W float in [0,1]
```

---

## 50. Summary of Fundamental Principles

1. Images are arrays; know your dtype and value range.
2. OpenCV uses BGR; most other tools use RGB.
3. Pillow is lazy; OpenCV is eager.
4. Preserve aspect ratio when resizing unless you have a reason not to.
5. Use vectorized operations; avoid Python-level pixel loops.
6. Validate image loads and dimensions before processing.
7. Handle EXIF orientation, especially for mobile photos.
8. Choose interpolation based on upscaling/downscaling and semantic content.
9. Be cautious with untrusted images and decompression bombs.
10. Separate training/validation/test augmentation policies.


## 51. Advanced OpenCV Modules

### 51.1 Background Subtraction

Background subtraction isolates moving foreground from a static or slowly changing background.

```python
import cv2

cap = cv2.VideoCapture("video.mp4")
fgbg = cv2.createBackgroundSubtractorMOG2()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    fgmask = fgbg.apply(frame)
    cv2.imshow("Foreground", fgmask)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```

Available algorithms:

| Algorithm | Notes |
|-----------|-------|
| `MOG2` | Gaussian mixture-based, supports shadows |
| `KNN` | K-nearest neighbors-based, good for dynamic backgrounds |
| `CNT` | Counting-based, lightweight |
| `GSOC` | Advanced, requires opencv-contrib |

### 51.2 Optical Flow

Optical flow estimates motion between frames.

**Lucas-Kanade sparse optical flow**:

```python
import numpy as np
import cv2

lk_params = dict(winSize=(15, 15), maxLevel=2,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
prev_pts = cv2.goodFeaturesToTrack(prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7)

next_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
next_pts, status, error = cv2.calcOpticalFlowPyrLK(prev_gray, next_gray, prev_pts, None, **lk_params)
```

**Dense optical flow (Farneback)**:

```python
flow = cv2.calcOpticalFlowFarneback(prev_gray, next_gray, None,
                                     pyr_scale=0.5, levels=3, winsize=15,
                                     iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
```

### 51.3 Face Detection and Landmarks

Haar cascades are lightweight but less accurate than deep-learning detectors.

```python
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

faces = face_cascade.detectMultiScale(gray, 1.3, 5)
for (x, y, w, h) in faces:
    cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
    roi_gray = gray[y:y+h, x:x+w]
    eyes = eye_cascade.detectMultiScale(roi_gray)
    for (ex, ey, ew, eh) in eyes:
        cv2.rectangle(img[y:y+h, x:x+w], (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
```

For landmarks, use `cv2.face.FaceRecognizer` (contrib) or external libraries like `dlib` and `mediapipe`.

### 51.4 Stereo Vision

Stereo matching computes disparity, which can be converted to depth.

```python
stereo = cv2.StereoBM_create(numDisparities=16, blockSize=15)
disparity = stereo.compute(left_gray, right_gray)

# Convert disparity to depth
# depth = (focal_length * baseline) / disparity
```

`StereoSGBM` generally produces better results than `StereoBM`:

```python
stereo = cv2.StereoSGBM_create(
    minDisparity=0,
    numDisparities=16,
    blockSize=5,
    P1=8 * 3 * 5 ** 2,
    P2=32 * 3 * 5 ** 2,
    disp12MaxDiff=1,
    uniquenessRatio=10,
    speckleWindowSize=100,
    speckleRange=32
)
```

### 51.5 Camera Calibration

Camera calibration estimates intrinsic and distortion parameters using a checkerboard pattern.

```python
import cv2
import numpy as np

objp = np.zeros((6*9, 3), np.float32)
objp[:, :2] = np.mgrid[0:9, 0:6].T.reshape(-1, 2)

objpoints = []
imgpoints = []

for fname in calibration_images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, (9, 6), None)
    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
        imgpoints.append(corners2)

ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
```

---

## 52. Panorama Stitching

### 52.1 Manual Pipeline

1. Detect features in both images.
2. Match descriptors.
3. Estimate homography with RANSAC.
4. Warp one image onto the other.

```python
import cv2
import numpy as np

orb = cv2.ORB_create()
kp1, des1 = orb.detectAndCompute(img1, None)
kp2, des2 = orb.detectAndCompute(img2, None)

bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
matches = bf.match(des1, des2)
matches = sorted(matches, key=lambda x: x.distance)

src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
warped = cv2.warpPerspective(img1, M, (img2.shape[1] + img1.shape[1], img2.shape[0]))
warped[0:img2.shape[0], 0:img2.shape[1]] = img2
```

### 52.2 OpenCV Stitcher

```python
stitcher = cv2.Stitcher.create()
status, panorama = stitcher.stitch([img1, img2])
```

---

## 53. Computational Photography

### 53.1 Image Denoising

OpenCV provides non-local means denoising:

```python
denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
```

Parameters:
- `h`: filter strength for luminance.
- `hColor`: filter strength for color.
- `templateWindowSize`: size of the patch used for comparison.
- `searchWindowSize`: size of the window used to find similar patches.

### 53.2 HDR Imaging

High Dynamic Range imaging merges multiple exposures.

```python
# Load exposure sequence
images = [cv2.imread(f"exp{i}.jpg") for i in range(3)]
exposures = np.array([0.0333, 0.25, 2.5], dtype=np.float32)

merge = cv2.createMergeDebevec()
hdr = merge.process(images, times=exposures)

tonemap = cv2.createTonemapReinhard(gamma=2.2, light_adapt=0.8)
ldr = tonemap.process(hdr)
ldr = np.clip(ldr * 255, 0, 255).astype(np.uint8)
```

### 53.3 Seamless Cloning Revisited

```python
mask = np.zeros(obj.shape[:2], np.uint8)
cv2.circle(mask, (obj.shape[1]//2, obj.shape[0]//2), 100, 255, -1)
center = (background.shape[1]//2, background.shape[0]//2)
cloned = cv2.seamlessClone(obj, background, mask, center, cv2.NORMAL_CLONE)
```

---

## 54. Image Restoration

### 54.1 Inpainting

Inpainting fills missing regions.

```python
mask = cv2.imread("mask.png", 0)
restored = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
```

Flags:
- `INPAINT_TELEA`: Fast Marching Method by Alexandru Telea.
- `INPAINT_NS`: Navier-Stokes based method.

### 54.2 Deconvolution

For simple motion blur removal, estimate the point-spread function (PSF) and apply deconvolution using Wiener filtering (available in scikit-image).

```python
from skimage import restoration

psf = np.ones((5, 5)) / 25
deconvolved, _ = restoration.unsupervised_wiener(gray, psf)
```

---

## 55. scikit-image Modules

### 55.1 Filtering

```python
from skimage import filters, morphology, restoration

edges = filters.sobel(gray)
thresh = filters.threshold_otsu(gray)
binary = gray > thresh
```

### 55.2 Morphology

```python
from skimage import morphology

cleaned = morphology.remove_small_objects(binary, min_size=64)
closed = morphology.closing(binary, morphology.disk(5))
```

### 55.3 Segmentation

```python
from skimage import segmentation, filters

edges = filters.sobel(gray)
markers = filters.rank.gradient(gray, morphology.disk(2)) < 10
markers = morphology.label(markers)
seg = segmentation.watershed(edges, markers)
```

### 55.4 Feature Detection

```python
from skimage import feature

corners = feature.corner_harris(gray)
coords = feature.corner_peaks(corners, min_distance=5)
```

### 55.5 Transform

```python
from skimage import transform

rotated = transform.rotate(img, angle=45, resize=True)
rescaled = transform.rescale(img, scale=0.5, anti_aliasing=True)
warped = transform.warp(img, tform)
```

### 55.6 Measure

```python
from skimage import measure

regions = measure.regionprops(measure.label(binary))
for region in regions:
    print(region.area, region.bbox, region.centroid)
```

---

## 56. Deep Learning Model Deployment

### 56.1 ONNX Export

```python
import torch

dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(model, dummy_input, "model.onnx",
                  input_names=["input"], output_names=["output"],
                  opset_version=11)
```

### 56.2 OpenCV DNN Inference

```python
net = cv2.dnn.readNetFromONNX("model.onnx")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
```

### 56.3 TensorRT / ONNX Runtime

For GPU inference, use ONNX Runtime or TensorRT:

```python
import onnxruntime as ort

session = ort.InferenceSession("model.onnx", providers=["CUDAExecutionProvider"])
outputs = session.run(None, {"input": input_array})
```

### 56.4 Quantization

Post-training quantization reduces model size and latency:

```python
import torch.quantization

model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
torch.quantization.prepare(model, inplace=True)
# calibrate with representative data
torch.quantization.convert(model, inplace=True)
```

---

## 57. Super-Resolution Basics

Classical super-resolution uses interpolation. Deep-learning methods (ESRGAN, Real-ESRGAN, SRGAN) learn mappings from low to high resolution.

```python
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel("EDSR_x4.pb")
sr.setModel("edsr", 4)
upscaled = sr.upsample(img)
```

For practical use, prefer pre-trained PyTorch models from `torchvision`, `timm`, or dedicated repos.

---

## 58. Style Transfer

Neural style transfer separates content and style using CNN features. PyTorch and TensorFlow both have tutorials. Pre-trained models are available via `torchvision` and `tensorflow-hub`.

```python
import torch
import torchvision.transforms as transforms

style_transform = transforms.Compose([
    transforms.Resize((512, 512)),
    transforms.ToTensor(),
])
```

---

## 59. GANs and Diffusion for Images

### 59.1 Generative Adversarial Networks

GANs generate images via a generator/discriminator game. Common architectures: DCGAN, StyleGAN, CycleGAN.

### 59.2 Diffusion Models

Diffusion models iteratively denoise latent variables to generate images. Stable Diffusion uses latent diffusion for efficiency.

```python
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")
pipe = pipe.to("cuda")
image = pipe("a photo of an astronaut riding a horse").images[0]
```

---

## 60. Image Search and Embeddings

### 60.1 CLIP Embeddings

CLIP maps images and text to a shared embedding space.

```python
import clip
import torch

model, preprocess = clip.load("ViT-B/32", device="cuda")
image = preprocess(pil_img).unsqueeze(0).to("cuda")
with torch.no_grad():
    image_features = model.encode_image(image)
```

### 60.2 Similarity Search

Normalize embeddings and use cosine similarity or FAISS for large-scale retrieval.

```python
cosine_sim = torch.nn.functional.cosine_similarity(a, b, dim=-1)
```

---

## 61. Augmentation for Specific Tasks

### 61.1 Classification

Random resized crop, horizontal flip, color jitter, normalization.

### 61.2 Object Detection

Flips, rotations, mosaic, mixup, cutmix. Bounding boxes must be transformed consistently.

```python
import albumentations as A

transform = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.RandomBrightnessContrast(p=0.2),
], bbox_params=A.BboxParams(format="pascal_voc", label_fields=["class_labels"]))
```

### 61.3 Segmentation

Spatial transforms must be applied identically to image and mask.

```python
transform = A.Compose([
    A.RandomResizedCrop(512, 512),
    A.HorizontalFlip(p=0.5),
], additional_targets={"mask": "mask"})

augmented = transform(image=img, mask=mask)
```

### 61.4 Keypoints

Keypoint transforms require careful handling of visibility flags.

```python
transform = A.Compose([
    A.HorizontalFlip(p=0.5),
], keypoint_params=A.KeypointParams(format="xy", remove_invisible=True))
```

---

## 62. Handling Class Imbalance in Segmentation

Use class weights or focal loss:

```python
weights = 1 / np.sqrt(class_counts)
weights = weights / weights.sum()
```

For semantic segmentation, the background often dominates; use weighted cross-entropy or Lovász-Softmax.

---

## 63. Working with Satellite and Aerial Imagery

- Often multi-band (RGB + NIR).
- Large file sizes; use tiling.
- GeoTIFF contains georeferencing metadata.
- Libraries: `rasterio`, `tifffile`, `opencv`, `Pillow`.

```python
import rasterio

with rasterio.open("satellite.tif") as src:
    img = src.read()   # shape (C, H, W)
    profile = src.profile
```

---

## 64. Medical Image Processing

Medical images often have:
- High bit depth (12, 16 bits).
- 3-D volumes (DICOM, NIfTI).
- Anisotropic voxel spacing.

```python
import SimpleITK as sitk

image = sitk.ReadImage("scan.nii.gz")
array = sitk.GetArrayFromImage(image)   # shape (D, H, W)
```

Visualization:
- Windowing for CT Hounsfield units.
- Multi-planar reconstruction (MPR).

---

## 65. 3-D Vision Basics

### 65.1 Point Clouds

Point clouds are collections of `(x, y, z)` coordinates. Libraries: Open3D, PyVista, PCL.

```python
import open3d as o3d

pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(points)
o3d.visualization.draw_geometries([pcd])
```

### 65.2 Depth Maps

A depth map stores per-pixel distance from the camera. Convert disparity to depth:

```python
depth = (focal_length * baseline) / (disparity + 1e-6)
```

---

## 66. Embedded and Edge Deployment

### 66.1 TensorFlow Lite

```python
import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_saved_model("saved_model")
tflite_model = converter.convert()
with open("model.tflite", "wb") as f:
    f.write(tflite_model)
```

### 66.2 ONNX Runtime Mobile

ONNX Runtime supports mobile and edge deployments with optimized execution providers.

### 66.3 OpenVINO

Intel OpenVINO optimizes models for Intel CPUs, GPUs, and VPUs.

```python
from openvino.runtime import Core

ie = Core()
model = ie.read_model("model.xml")
compiled = ie.compile_model(model, "CPU")
```

---

## 67. Synthetic Data Generation

Synthetic data reduces annotation costs. Tools include:
- BlenderProc
- NVIDIA Isaac Sim
- Unity Perception
- `imgaug`, `albumentations` for 2-D augmentations

---

## 68. Image Datasets

Common public datasets:

| Dataset | Task | Classes/Notes |
|---------|------|---------------|
| ImageNet | Classification | 1000 classes |
| CIFAR-10/100 | Classification | 10/100 classes, 32x32 |
| MNIST/Fashion-MNIST | Classification | Grayscale digits |
| COCO | Detection, segmentation, captioning | 80 object categories |
| Pascal VOC | Detection, segmentation | 20 classes |
| Open Images | Detection, segmentation | 600 classes |
| KITTI | Autonomous driving | stereo, LiDAR |

---

## 69. Evaluation Metrics by Task

### 69.1 Classification

- Accuracy, precision, recall, F1-score.
- Confusion matrix.
- ROC-AUC.

### 69.2 Object Detection

- mAP (mean Average Precision) at IoU thresholds.
- AP per class.
- IoU (Intersection over Union).

```python
def iou(box_a, box_b):
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    return inter / (area_a + area_b - inter)
```

### 69.3 Segmentation

- Pixel accuracy.
- Mean IoU.
- Dice coefficient (F1 for segmentation).

```python
def dice_score(pred, target):
    intersection = (pred * target).sum()
    return 2 * intersection / (pred.sum() + target.sum())
```

---

## 70. Reproducibility

Set seeds for reproducible augmentation and sampling:

```python
import random
import numpy as np
import torch

random.seed(42)
np.random.seed(42)
torch.manual_seed(42)
torch.cuda.manual_seed_all(42)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
```

For Albumentations:

```python
import albumentations as A
A.set_seed(42)
```

---

## 71. Additional Useful Code Snippets

### 71.1 Add Padding to Make Square

```python
def pad_to_square(img, fill=0):
    h, w = img.shape[:2]
    size = max(h, w)
    pad_h = (size - h) // 2
    pad_w = (size - w) // 2
    return cv2.copyMakeBorder(img, pad_h, size - h - pad_h,
                              pad_w, size - w - pad_w,
                              cv2.BORDER_CONSTANT, value=fill)
```

### 71.2 Center Crop

```python
def center_crop(img, crop_h, crop_w):
    h, w = img.shape[:2]
    top = (h - crop_h) // 2
    left = (w - crop_w) // 2
    return img[top:top+crop_h, left:left+crop_w]
```

### 71.3 Convert Label Mask to Color

```python
def mask_to_color(mask, palette):
    color = np.zeros((*mask.shape, 3), dtype=np.uint8)
    for label, (r, g, b) in palette.items():
        color[mask == label] = [r, g, b]
    return color
```

### 71.4 Generate a Heatmap Overlay

```python
def overlay_heatmap(img, heatmap, alpha=0.5, colormap=cv2.COLORMAP_JET):
    hm = cv2.applyColorMap(np.uint8(255 * heatmap), colormap)
    return cv2.addWeighted(img, 1 - alpha, hm, alpha, 0)
```

---

## 72. Testing Image Code

Write unit tests for image utilities:

```python
import numpy as np
import pytest

def test_resize_preserves_aspect():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = resize_keep_aspect(img, 224)
    assert out.shape[0] <= 224
    assert out.shape[1] <= 224
    assert abs(out.shape[1] / out.shape[0] - 640 / 480) < 1e-5
```

Use synthetic images for tests to avoid checking large binary files into version control.

---

## 73. Documentation and Communication

When writing about image processing code:
- State color space explicitly (RGB vs BGR).
- State array shape conventions (`H, W, C` vs `C, H, W`).
- Include value ranges (`uint8 [0,255]`, `float [0,1]`, normalized).
- Note whether a transform is in-place or returns a copy.
- Document expected input sizes and dtypes.

---

## 74. Future Trends

- **Vision Transformers (ViT)**: replace CNN backbones with transformer architectures.
- **Self-supervised learning**: learn representations without labels (MAE, DINO).
- **Neural rendering**: synthesize novel views (NeRF, Gaussian Splatting).
- **Multimodal models**: combine vision and language (CLIP, GPT-4V, LLaVA).
- **Efficient inference**: quantization, pruning, knowledge distillation for edge devices.

---

## 75. Final Fact Sheet

Keep these facts at top of mind:

- OpenCV default color order is BGR; Pillow and matplotlib use RGB.
- OpenCV image shape is `(H, W, C)`; PyTorch tensor is `(C, H, W)`.
- Pillow loads lazily; call `.load()` or use the image before closing the file.
- Always check `cv2.imread` for `None`.
- JPEG is lossy; PNG supports transparency and is lossless.
- Resize masks with nearest-neighbor interpolation.
- Normalize images consistently with the pretrained model's training setup.
- Augment training data only, never validation/test data.
- Handle EXIF orientation for mobile and camera images.
- Validate dimensions, dtypes, and value ranges before model inference.


## 76. Detailed OpenCV Function Reference

### 76.1 Core Functions

| Function | Purpose |
|----------|---------|
| `cv2.imread(path, flags)` | Load image from file |
| `cv2.imwrite(path, img, params)` | Save image to file |
| `cv2.imshow(name, img)` | Display image in window |
| `cv2.waitKey(delay)` | Wait for key event |
| `cv2.cvtColor(src, code)` | Convert color spaces |
| `cv2.resize(src, dsize, fx, fy, interpolation)` | Resize image |
| `cv2.flip(src, flipCode)` | Flip image |
| `cv2.split(src)` | Split channels |
| `cv2.merge(channels)` | Merge channels |
| `cv2.copyMakeBorder` | Add padding |
| `cv2.addWeighted` | Blend two images |
| `cv2.bitwise_and/or/xor/not` | Bitwise operations |
| `cv2.inRange` | Range thresholding |
| `cv2.compareHist` | Compare histograms |

### 76.2 Filtering Functions

| Function | Purpose |
|----------|---------|
| `cv2.blur` | Averaging filter |
| `cv2.GaussianBlur` | Gaussian smoothing |
| `cv2.medianBlur` | Median filtering |
| `cv2.bilateralFilter` | Edge-preserving smoothing |
| `cv2.filter2D` | Custom kernel convolution |
| `cv2.Sobel` | Sobel edge detector |
| `cv2.Laplacian` | Laplacian edge detector |
| `cv2.Canny` | Canny edge detector |
| `cv2.erode` | Erosion |
| `cv2.dilate` | Dilation |
| `cv2.morphologyEx` | Advanced morphology |

### 76.3 Geometric Transform Functions

| Function | Purpose |
|----------|---------|
| `cv2.getRotationMatrix2D` | 2-D rotation matrix |
| `cv2.warpAffine` | Affine transform |
| `cv2.getAffineTransform` | Affine from 3 point pairs |
| `cv2.getPerspectiveTransform` | Perspective from 4 point pairs |
| `cv2.warpPerspective` | Perspective transform |
| `cv2.remap` | Generic remapping |
| `cv2.pyrDown` / `cv2.pyrUp` | Pyramid levels |

### 76.4 Contour Functions

| Function | Purpose |
|----------|---------|
| `cv2.findContours` | Find contours |
| `cv2.drawContours` | Draw contours |
| `cv2.contourArea` | Contour area |
| `cv2.arcLength` | Contour perimeter |
| `cv2.approxPolyDP` | Polygon approximation |
| `cv2.convexHull` | Convex hull |
| `cv2.boundingRect` | Upright bounding box |
| `cv2.minAreaRect` | Rotated bounding box |
| `cv2.minEnclosingCircle` | Minimum enclosing circle |
| `cv2.fitEllipse` | Fitted ellipse |
| `cv2.matchShapes` | Shape matching |
| `cv2.moments` | Spatial moments |

### 76.5 Feature Functions

| Function | Purpose |
|----------|---------|
| `cv2.cornerHarris` | Harris corners |
| `cv2.goodFeaturesToTrack` | Shi-Tomasi corners |
| `cv2.ORB_create` | ORB detector/descriptor |
| `cv2.SIFT_create` | SIFT detector/descriptor |
| `cv2.BFMatcher` | Brute-force matcher |
| `cv2.FlannBasedMatcher` | Fast approximate matcher |
| `cv2.findHomography` | Estimate homography |
| `cv2.warpPerspective` | Apply homography |

### 76.6 Video Functions

| Function | Purpose |
|----------|---------|
| `cv2.VideoCapture` | Open video or camera |
| `cv2.VideoWriter` | Write video |
| `cv2.VideoWriter_fourcc` | FourCC codec code |
| `cv2.calcOpticalFlowPyrLK` | Sparse optical flow |
| `cv2.calcOpticalFlowFarneback` | Dense optical flow |
| `cv2.createBackgroundSubtractorMOG2` | Background subtraction |
| `cv2.createBackgroundSubtractorKNN` | KNN background subtraction |

---

## 77. Detailed Pillow API Reference

### 77.1 Image Module Functions

| Function | Purpose |
|----------|---------|
| `Image.open(fp)` | Open image file |
| `Image.new(mode, size, color)` | Create blank image |
| `Image.fromarray(arr, mode)` | NumPy array to image |
| `Image.merge(mode, bands)` | Merge band images |
| `Image.blend(im1, im2, alpha)` | Blend images |
| `Image.composite(im1, im2, mask)` | Composite with mask |
| `Image.eval(image, function)` | Apply function per pixel value |

### 77.2 Image Methods

| Method | Purpose |
|--------|---------|
| `convert(mode)` | Change mode/color space |
| `copy()` | Copy image |
| `crop(box)` | Crop region |
| `filter(filter)` | Apply filter |
| `getbbox()` | Bounding box of non-zero content |
| `getchannel(channel)` | Extract single channel |
| `getcolors(maxcolors)` | Count colors |
| `getpixel(xy)` | Read single pixel |
| `histogram()` | Compute histogram |
| `paste(im, box, mask)` | Paste image |
| `point(lut)` | Apply lookup table |
| `putalpha(alpha)` | Set alpha channel |
| `putdata(data)` | Set pixel data |
| `putpixel(xy, value)` | Set single pixel |
| `quantize(colors)` | Reduce colors |
| `resize(size, resample)` | Resize |
| `rotate(angle, ...)` | Rotate |
| `save(fp, format, **params)` | Save image |
| `show()` | Display image |
| `split()` | Split bands |
| `thumbnail(size)` | Make thumbnail |
| `tobytes()` | Raw pixel bytes |
| `transform(size, method, data)` | Geometric transform |
| `transpose(method)` | Flip/rotate 90° |
| `verify()` | Verify file integrity |

### 77.3 ImageFilter Filters

| Filter | Effect |
|--------|--------|
| `BLUR` | Gaussian-like blur |
| `CONTOUR` | Contour effect |
| `DETAIL` | Enhance details |
| `EDGE_ENHANCE` | Enhance edges |
| `EDGE_ENHANCE_MORE` | Stronger edge enhancement |
| `EMBOSS` | Emboss effect |
| `FIND_EDGES` | Edge detection |
| `SHARPEN` | Sharpen |
| `SMOOTH` | Smooth |
| `SMOOTH_MORE` | Stronger smooth |
| `GaussianBlur(radius)` | Gaussian blur |
| `UnsharpMask(radius, percent, threshold)` | Unsharp mask |
| `MedianFilter(size)` | Median filter |
| `ModeFilter(size)` | Mode filter |
| `MaxFilter(size)` | Maximum filter |
| `MinFilter(size)` | Minimum filter |

### 77.4 ImageEnhance Classes

| Class | Parameter |
|-------|-----------|
| `Brightness` | 0.0=black, 1.0=original, >1=brighter |
| `Color` | 0.0=grayscale, 1.0=original, >1=more saturated |
| `Contrast` | 0.0=gray, 1.0=original, >1=more contrast |
| `Sharpness` | 0.0=blur, 1.0=original, >1=sharper |

### 77.5 ImageDraw Primitives

| Method | Purpose |
|--------|---------|
| `arc` | Draw arc |
| `bitmap` | Draw bitmap |
| `chord` | Draw chord |
| `ellipse` | Draw ellipse |
| `line` | Draw line |
| `pieslice` | Draw pie slice |
| `point` | Draw point |
| `polygon` | Draw polygon |
| `rectangle` | Draw rectangle |
| `text` | Draw text |
| `textbbox` | Get text bounding box |
| `textlength` | Get text length |

### 77.6 ImageFont

```python
from PIL import ImageFont
font = ImageFont.truetype("arial.ttf", 40)
font = ImageFont.load_default()
```

---

## 78. Detailed scikit-image API Reference

### 78.1 Submodules

| Submodule | Purpose |
|-----------|---------|
| `skimage.color` | Color space conversions |
| `skimage.data` | Sample images |
| `skimage.draw` | Drawing primitives |
| `skimage.exposure` | Intensity/exposure adjustments |
| `skimage.feature` | Feature detection (corners, ORB, HOG, etc.) |
| `skimage.filters` | Linear/non-linear filters |
| `skimage.graph` | Graph-based segmentation |
| `skimage.io` | Image I/O |
| `skimage.measure` | Measurement and region properties |
| `skimage.metrics` | Image quality metrics |
| `skimage.morphology` | Morphological operations |
| `skimage.restoration` | Restoration (denoising, deconvolution) |
| `skimage.segmentation` | Segmentation algorithms |
| `skimage.transform` | Geometric transforms |
| `skimage.util` | Utility functions |

### 78.2 Common Functions

```python
from skimage import data, filters, morphology, segmentation, measure, transform, util

# Sample images
camera = data.camera()
coins = data.coins()
astronaut = data.astronaut()

# Thresholding
thresh = filters.threshold_otsu(coins)
binary = coins > thresh

# Morphology
cleaned = morphology.remove_small_objects(binary)

# Segmentation
labels = measure.label(cleaned)
regions = measure.regionprops(labels)

# Transform
rotated = transform.rotate(astronaut, angle=45, resize=True)

# Utility
padded = util.pad(camera, pad_width=10, mode='constant')
cropped = util.crop(camera, crop_width=10)
```

---

## 79. Image Processing Theory

### 79.1 Convolution

Convolution slides a kernel over an image, computing a weighted sum at each position:

```
(I * K)(x, y) = sum_i sum_j I(x+i, y+j) * K(i, j)
```

Border handling modes:

| Mode | Behavior |
|------|----------|
| Constant | Fill with constant value |
| Reflect | Reflect edge pixels |
| Replicate | Repeat edge pixel |
| Wrap | Wrap around |

### 79.2 Linear Filtering

Averaging kernel:

```
1/9 * [[1, 1, 1],
       [1, 1, 1],
       [1, 1, 1]]
```

Gaussian kernel approximates a 2-D Gaussian function. Larger sigma requires larger kernel.

### 79.3 Edge Detection Theory

Edges correspond to rapid intensity changes. Gradient magnitude:

```
G = sqrt(Gx^2 + Gy^2)
theta = atan2(Gy, Gx)
```

Sobel operator estimates gradients using finite differences. Canny adds non-maximum suppression and hysteresis.

### 79.4 Morphology Theory

Morphological operations are defined by a structuring element `B`:

- **Erosion**: `(I ⊖ B)(x) = min_{b in B} I(x + b)`
- **Dilation**: `(I ⊕ B)(x) = max_{b in B} I(x + b)`
- **Opening**: erosion followed by dilation (removes small objects).
- **Closing**: dilation followed by erosion (fills small holes).

### 79.5 Histogram Equalization Theory

Transform pixel intensity `r` to `s` using the cumulative distribution function (CDF):

```
s = T(r) = (L - 1) * CDF(r)
```

CLAHE limits amplification to avoid noise amplification in homogeneous regions.

---

## 80. Detailed Code Recipes

### 80.1 Load Image Safely

```python
import cv2
from PIL import Image
import numpy as np

def load_image_cv2(path, mode="rgb"):
    """Load image with OpenCV, return as RGB or BGR."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {path}")
    if mode == "rgb" and img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img

def load_image_pil(path, mode="RGB"):
    """Load image with Pillow, auto-rotate by EXIF."""
    from PIL import ImageOps
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if mode:
            im = im.convert(mode)
        return im.copy()
```

### 80.2 Save Image with Correct Color Space

```python
def save_image_cv2(img, path, mode="rgb"):
    if mode == "rgb" and img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), img)
```

### 80.3 Resize with Aspect Ratio

```python
def resize_with_aspect_ratio(img, max_size, interpolation=cv2.INTER_AREA):
    h, w = img.shape[:2]
    scale = min(max_size / h, max_size / w)
    if scale >= 1.0:
        return img
    new_size = (int(w * scale), int(h * scale))
    return cv2.resize(img, new_size, interpolation=interpolation)
```

### 80.4 Make Square by Padding

```python
def make_square(img, size, fill=(0, 0, 0)):
    h, w = img.shape[:2]
    scale = size / max(h, w)
    resized = cv2.resize(img, (int(w * scale), int(h * scale)))
    ph = (size - resized.shape[0]) // 2
    pw = (size - resized.shape[1]) // 2
    return cv2.copyMakeBorder(resized, ph, size - resized.shape[0] - ph,
                              pw, size - resized.shape[1] - pw,
                              cv2.BORDER_CONSTANT, value=fill)
```

### 80.5 Standardize for PyTorch

```python
import torch
from torchvision import transforms

def make_torch_transform(input_size=224):
    return transforms.Compose([
        transforms.Resize(int(input_size * 1.14)),
        transforms.CenterCrop(input_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
```

### 80.6 Convert PyTorch Output to Image

```python
def denormalize(tensor, mean, std):
    mean = torch.tensor(mean).view(-1, 1, 1)
    std = torch.tensor(std).view(-1, 1, 1)
    return tensor * std + mean

def tensor_to_image(tensor):
    img = tensor.detach().cpu().clamp(0, 1).numpy()
    img = np.transpose(img, (1, 2, 0))
    return (img * 255).astype(np.uint8)
```

### 80.7 Batch Resize Directory

```python
from pathlib import Path
from PIL import Image

def batch_resize(input_dir, output_dir, size=(256, 256)):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in Path(input_dir).glob("*"):
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im)
                im.thumbnail(size)
                im.save(output_dir / f"{path.stem}.jpg")
        except Exception as e:
            print(f"Skipping {path}: {e}")
```

---

## 81. More on Color Science

### 81.1 sRGB

sRGB is the default color space for web and most consumer images. Its gamma curve approximates `gamma ≈ 2.2`.

### 81.2 Adobe RGB

Adobe RGB has a wider gamut than sRGB. Converting without a profile can cause color shifts.

### 81.3 CIE LAB

LAB separates lightness (`L*`) from color (`a*`, `b*`). Euclidean distance in LAB is approximately perceptually uniform.

### 81.4 YCbCr

Used in JPEG and video. `Y` is luma; `Cb` and `Cr` are chroma. Chroma is often subsampled (4:2:0, 4:2:2).

---

## 82. Image Compression Details

### 82.1 JPEG Encoding Steps

1. Color space conversion to YCbCr.
2. Chroma subsampling (optional).
3. Block splitting into 8x8 blocks.
4. Discrete Cosine Transform (DCT).
5. Quantization (quality setting controls quantization table).
6. Zig-zag scan and entropy coding.

### 82.2 PNG Encoding

1. Optional filtering of rows (None, Sub, Up, Average, Paeth).
2. Deflate compression.

### 82.3 WebP

WebP supports both lossy (VP8-based) and lossless (WebP-lossless) modes, plus animation and alpha.

---

## 83. Memory and Efficiency

### 83.1 Avoid Copies

Use views when possible:

```python
red = img[:, :, 0]        # view, not copy
red_copy = img[:, :, 0].copy()
```

### 83.2 In-Place Operations

NumPy in-place operations reduce memory:

```python
img_float = img.astype(np.float32)
img_float /= 255.0   # in-place division
```

### 83.3 Chunking Large Images

Process large images in tiles:

```python
def process_tiles(img, tile_size, process_fn):
    h, w = img.shape[:2]
    out = np.zeros_like(img)
    for y in range(0, h, tile_size):
        for x in range(0, w, tile_size):
            tile = img[y:y+tile_size, x:x+tile_size]
            out[y:y+tile_size, x:x+tile_size] = process_fn(tile)
    return out
```

### 83.4 Memory-Mapped Files

```python
import numpy as np

arr = np.memmap("large.bin", dtype=np.uint8, mode="r", shape=(10000, 1024, 1024, 3))
```

---

## 84. Image File Metadata

### 84.1 Reading Metadata with imageio

```python
import imageio.v3 as iio

meta = iio.immeta("photo.jpg")
print(meta.get("Orientation"))
print(meta.get("DateTime"))
```

### 84.2 Reading with exifread

```python
import exifread

with open("photo.jpg", "rb") as f:
    tags = exifread.process_file(f)
    print(tags.get("Image Orientation"))
```

### 84.3 Writing XMP

Pillow supports XMP when saving some formats:

```python
im.save("out.jpg", xmp=b"<?xml version='1.0'?><x:xmpmeta ...>")
```

---

## 85. Common Transform Code

### 85.1 Random Affine

```python
import cv2
import numpy as np

def random_affine(img, angle=15, translate=0.1, scale=0.1, shear=10):
    h, w = img.shape[:2]
    center = (w / 2, h / 2)
    angle = np.random.uniform(-angle, angle)
    tx = np.random.uniform(-translate, translate) * w
    ty = np.random.uniform(-translate, translate) * h
    scale = np.random.uniform(1 - scale, 1 + scale)
    shear = np.random.uniform(-shear, shear)

    M = cv2.getRotationMatrix2D(center, angle, scale)
    M[:, 2] += [tx, ty]
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT)
```

### 85.2 Perspective Distortion

```python
def random_perspective(img, distortion=0.2):
    h, w = img.shape[:2]
    margin = distortion * min(h, w)

    pts1 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    pts2 = np.float32([
        [np.random.uniform(0, margin), np.random.uniform(0, margin)],
        [np.random.uniform(w - margin, w), np.random.uniform(0, margin)],
        [np.random.uniform(w - margin, w), np.random.uniform(h - margin, h)],
        [np.random.uniform(0, margin), np.random.uniform(h - margin, h)],
    ])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    return cv2.warpPerspective(img, M, (w, h))
```

---

## 86. Error Handling Patterns

### 86.1 Graceful Image Loading

```python
def load_or_default(path, default_shape=(224, 224, 3)):
    try:
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError("cv2.imread returned None")
        return img
    except Exception as e:
        print(f"Failed to load {path}: {e}")
        return np.zeros(default_shape, dtype=np.uint8)
```

### 86.2 Dimension Normalization

```python
def ensure_rgb(img):
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    if img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img.dtype == np.uint8 else img
    raise ValueError(f"Unexpected image shape: {img.shape}")
```

---

## 87. Testing and Profiling

### 87.1 Profile a Pipeline

```python
import time

def time_stage(fn, img):
    start = time.perf_counter()
    out = fn(img)
    elapsed = time.perf_counter() - start
    return out, elapsed
```

### 87.2 Visual Regression Tests

Compare pipeline outputs against reference images:

```python
from skimage.metrics import structural_similarity as ssim

def images_match(a, b, threshold=0.99):
    return ssim(a, b, channel_axis=2, data_range=255) >= threshold
```

---

## 88. Summary Tables

### 88.1 Library Strengths

| Library | Best For | Weakness |
|---------|----------|----------|
| Pillow | High-level editing, format support, thumbnails | Slower than OpenCV for arrays |
| OpenCV | Real-time processing, video, classical CV | BGR convention, verbose API |
| scikit-image | Research, readable code, scientific formats | Slower than OpenCV |
| imageio | Unified I/O, multi-frame, metadata | Less manipulation functionality |
| Albumentations | Deep-learning augmentation | Requires NumPy RGB arrays |
| torchvision | PyTorch preprocessing | Tied to PyTorch |
| Kornia | Differentiable CV in PyTorch | GPU required for best performance |

### 88.2 When to Use Which Interpolation

| Scenario | Interpolation |
|----------|---------------|
| Downscale photo | `INTER_AREA` |
| Upscale photo | `INTER_CUBIC` or `INTER_LANCZOS4` |
| Resize label mask | `INTER_NEAREST` |
| Resize depth map | `INTER_NEAREST` or `INTER_LINEAR` |
| Real-time preview | `INTER_LINEAR` |
| Preserve hard edges | `INTER_NEAREST` |

### 88.3 Color Conversion Summary

| From | To | OpenCV Code |
|------|-----|-------------|
| BGR | RGB | `COLOR_BGR2RGB` |
| BGR | Gray | `COLOR_BGR2GRAY` |
| BGR | HSV | `COLOR_BGR2HSV` |
| BGR | LAB | `COLOR_BGR2LAB` |
| BGR | YCrCb | `COLOR_BGR2YCrCb` |
| Gray | BGR | `COLOR_GRAY2BGR` |
| RGB | BGR | `COLOR_RGB2BGR` |
| RGB | Gray | `COLOR_RGB2GRAY` |
| HSV | BGR | `COLOR_HSV2BGR` |

---

## 89. Bibliographic Notes

This file synthesizes knowledge from:

- OpenCV official documentation and tutorials.
- Pillow (PIL Fork) reference documentation.
- scikit-image user guide and API reference.
- NumPy documentation.
- Real Python Pillow tutorial.
- PyTorch and torchvision documentation.
- Albumentations documentation.
- General computer-vision textbooks (Gonzalez & Woods, Szeliski).

The facts are kept practical and code-first so an AI coding assistant can recall and apply them directly.


## 90. Advanced Topics in Image Acquisition

### 90.1 Camera Parameters

Important camera parameters:

- **Resolution**: number of pixels (width x height).
- **Frame rate (FPS)**: frames per second.
- **Exposure time**: duration the sensor collects light.
- **ISO / gain**: sensitivity amplification.
- **Aperture**: controls depth of field and light intake.
- **White balance**: removes color casts from illumination.
- **Focus**: lens position for sharp images.

### 90.2 Sensor Types

- **CCD**: Charge-Coupled Device, low noise, older technology.
- **CMOS**: Complementary Metal-Oxide-Semiconductor, dominant in modern cameras, lower power.
- **Rolling shutter**: reads rows sequentially, can cause artifacts with fast motion.
- **Global shutter**: reads all pixels simultaneously, better for moving objects.

### 90.3 Bayer Pattern

Most color sensors use a Bayer filter mosaic (RGGB, BGGR, GRBG, GBRG). Demosaicing reconstructs full RGB from raw sensor data. OpenCV and raw processing libraries handle demosaicing.

```python
import rawpy

with rawpy.imread("raw.dng") as raw:
    rgb = raw.postprocess(demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
```

---

## 91. Lighting and Optics

### 91.1 Common Lighting Issues

- **Overexposure**: clipped highlights, loss of detail.
- **Underexposure**: noisy shadows.
- **Backlighting**: subject underexposed against bright background.
- **Color casts**: from tungsten, fluorescent, or LED lighting.
- **Specular highlights**: reflective hotspots.
- **Shadows**: can obscure features.

### 91.2 Lens Effects

- **Distortion**: barrel or pincushion.
- **Chromatic aberration**: color fringing at high-contrast edges.
- **Vignetting**: darkening at corners.
- **Depth of field**: range of acceptable focus.
- **Bokeh**: aesthetic quality of out-of-focus blur.

---

## 92. Preprocessing Pipelines by Application

### 92.1 Document Scanning

1. Convert to grayscale.
2. Gaussian blur to reduce noise.
3. Adaptive thresholding or Canny edge detection.
4. Find contours of the largest quadrilateral.
5. Apply perspective transform to rectify.
6. Optional: sharpen and binarize.

### 92.2 OCR Preprocessing

1. Grayscale conversion.
2. Noise reduction (median/Gaussian).
3. Contrast stretching or thresholding.
4. Deskew (rotate to correct text angle).
5. Resize to target DPI (usually 200-300).
6. Binarization.

### 92.3 Face Recognition Preprocessing

1. Detect face bounding box.
2. Align face using eye coordinates.
3. Normalize illumination.
4. Resize to model input size (e.g., 112x112, 160x160).
5. Normalize pixel values.

### 92.4 Autonomous Driving Perception

1. Distortion correction.
2. Color normalization.
3. Resize and letterbox.
4. Temporal filtering.
5. Multi-camera fusion.

---

## 93. Data Annotation Formats

### 93.1 COCO

JSON format with images, annotations, categories. Bounding boxes are `[x, y, width, height]`.

### 93.2 Pascal VOC

XML per image with `bndbox` (`xmin`, `ymin`, `xmax`, `ymax`).

### 93.3 YOLO

Text file per image with one line per object: `class_id cx cy w h` normalized to `[0, 1]`.

### 93.4 LabelMe / JSON Polygon

Polygon segmentation masks in JSON.

---

## 94. Annotation Tools

Popular open-source annotation tools:

- **LabelImg**: bounding boxes, Pascal VOC / YOLO.
- **CVAT**: comprehensive, supports detection/segmentation/video.
- **LabelMe**: polygons, segmentation.
- **Roboflow**: end-to-end dataset management and augmentation.
- **VoTT**: Microsoft annotation tool.

---

## 95. Dataset Quality

### 95.1 Common Dataset Issues

- Class imbalance.
- Label noise.
- Duplicate or near-duplicate images.
- Domain shift between train and test.
- Incorrect EXIF orientation.
- Inconsistent bounding box formats.
- Leakage between splits.

### 95.2 Validation Checks

```python
def validate_bbox(box, img_w, img_h):
    x, y, w, h = box
    return 0 <= x < img_w and 0 <= y < img_h and w > 0 and h > 0
```

---

## 96. Domain Adaptation

Domain adaptation transfers knowledge from a labeled source domain to an unlabeled target domain.

Techniques:

- Fine-tuning on target data.
- Adversarial domain adaptation.
- Self-training with pseudo-labels.
- Normalization alignment.

---

## 97. Active Learning

Active learning selects the most informative unlabeled samples for annotation.

Selection strategies:

- Uncertainty sampling (lowest confidence / highest entropy).
- Diversity sampling.
- Expected model change.

---

## 98. Model Interpretability for Vision

### 98.1 Class Activation Mapping (CAM)

CAM highlights image regions important for classification.

### 98.2 Grad-CAM

Grad-CAM uses gradients flowing into the final convolutional layer.

```python
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image

cam = GradCAM(model=model, target_layers=[model.layer4[-1]])
grayscale_cam = cam(input_tensor=input_tensor)
visualization = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)
```

### 98.3 Saliency Maps

Compute gradient of class score with respect to input pixels.

---

## 99. Adversarial Examples

Small, often imperceptible perturbations can cause misclassification.

Defense strategies:

- Adversarial training.
- Input preprocessing (denoising, JPEG compression).
- Certified defenses.

---

## 100. Final Checklist for Vision Tasks

Before training or deploying a vision model:

- [ ] Images are loaded in the correct color space.
- [ ] EXIF orientation is applied.
- [ ] Train/val/test splits are clean.
- [ ] Augmentation matches the task (classification/detection/segmentation).
- [ ] Normalization matches pretrained weights.
- [ ] Label format matches model expectation.
- [ ] Input size matches model.
- [ ] Masks use nearest-neighbor resizing.
- [ ] Validation metrics are appropriate.
- [ ] Model is tested on real-world data distribution.
- [ ] Inference pipeline handles errors gracefully.
- [ ] Memory and latency meet requirements.
