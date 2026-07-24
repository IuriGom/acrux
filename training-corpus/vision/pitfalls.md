# Vision: Common Pitfalls, Edge Cases, and How to Avoid Them

This file catalogs common mistakes, edge cases, performance traps, security issues, and debugging tips for image processing and computer vision in Python.

---

## 1. BGR vs. RGB Confusion

**Pitfall**: OpenCV loads color images in BGR order, but most other libraries (Pillow, matplotlib, scikit-image, PyTorch, TensorFlow) expect RGB. Passing a BGR image to `plt.imshow` produces colors with swapped red and blue channels.

```python
import cv2
import matplotlib.pyplot as plt

img = cv2.imread("photo.jpg")   # BGR
plt.imshow(img)                 # WRONG: red and blue swapped
plt.show()
```

**Fix**:

```python
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
plt.imshow(img_rgb)
plt.show()
```

**Rule of thumb**: explicitly convert color spaces at library boundaries. Never assume a 3-channel array is RGB unless you created it or the source guarantees it.

---

## 2. Assuming OpenCV `imread` Always Succeeds

**Pitfall**: `cv2.imread` returns `None` when a file is missing, corrupted, or in an unsupported format. Operating on `None` causes confusing errors downstream.

```python
img = cv2.imread("missing.jpg")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)   # TypeError
```

**Fix**:

```python
img = cv2.imread("photo.jpg")
if img is None:
    raise FileNotFoundError("Failed to load photo.jpg")
```

---

## 3. Pillow Lazy Loading and Closed File Handles

**Pitfall**: `Image.open()` does not load pixels immediately. If you return the image object from a function and the file handle goes out of scope, later access fails.

```python
def load(path):
    return Image.open(path)   # file still open

im = load("photo.jpg")
# ... later ...
print(im.size)   # may raise ValueError: operation on closed file
```

**Fix**:

```python
def load(path):
    with Image.open(path) as im:
        return im.copy()   # pixels loaded, file closed
```

---

## 4. Forgetting EXIF Orientation

**Pitfall**: Mobile photos often store pixels in landscape orientation with an EXIF `Orientation` tag indicating portrait. Ignoring the tag produces sideways images.

**Fix**:

```python
from PIL import Image, ImageOps

with Image.open(path) as im:
    im = ImageOps.exif_transpose(im)
```

OpenCV does not apply EXIF orientation. Either load with Pillow and convert, or read the orientation tag and rotate manually.

---

## 5. Integer Overflow in NumPy

**Pitfall**: `uint8` arithmetic wraps around at 255. Adding two bright images can produce dark artifacts.

```python
import numpy as np
a = np.full((10, 10), 200, dtype=np.uint8)
b = np.full((10, 10), 100, dtype=np.uint8)
print(a + b)   # wraps to 44
```

**Fix**: Cast to a wider type before arithmetic, then clip.

```python
c = np.clip(a.astype(np.int16) + b, 0, 255).astype(np.uint8)
```

---

## 6. Wrong Interpolation for Masks

**Pitfall**: Resizing a segmentation mask with bilinear or cubic interpolation creates new class labels and soft boundaries.

```python
mask_small = cv2.resize(mask, (256, 256), interpolation=cv2.INTER_LINEAR)
# mask may now contain values that do not correspond to any class
```

**Fix**: Always use nearest-neighbor interpolation for label masks.

```python
mask_small = cv2.resize(mask, (256, 256), interpolation=cv2.INTER_NEAREST)
```

---

## 7. Mixing Size Conventions

**Pitfall**: Libraries use different size orderings.

- OpenCV `resize`: `(width, height)`.
- NumPy shape: `(height, width, channels)`.
- PyTorch tensor: `(C, H, W)`.
- Pillow: `(width, height)`.

```python
# Wrong: passing (h, w) to cv2.resize
cv2.resize(img, img.shape[:2])   # incorrect dimensions
```

**Fix**: Be explicit.

```python
h, w = img.shape[:2]
cv2.resize(img, (w // 2, h // 2))
```

---

## 8. Lossy JPEG Re-encoding

**Pitfall**: Repeatedly loading and saving JPEG degrades quality because JPEG is lossy. Each save introduces new compression artifacts.

**Fix**: Use PNG or a lossless format for intermediate results. Save JPEG only as the final output.

---

## 9. Saving RGBA as JPEG

**Pitfall**: JPEG does not support transparency. Saving an RGBA image with Pillow silently drops the alpha channel or raises an error depending on the version.

**Fix**: Convert to RGB before saving as JPEG.

```python
im.convert("RGB").save("output.jpg", quality=90)
```

---

## 10. In-Place Modification Surprises

**Pitfall**: NumPy views share memory. Modifying a view changes the original array.

```python
patch = img[100:200, 100:200]
patch[:] = 0   # also modifies img
```

**Fix**: Use `.copy()` when you need an independent array.

```python
patch = img[100:200, 100:200].copy()
```

---

## 11. Normalizing Already-Normalized Data

**Pitfall**: Applying ImageNet normalization twice divides by 255 twice and uses the wrong mean/std scale.

```python
# WRONG if transform already includes ToTensor + Normalize
tensor = transform(img)
normalized = tensor / 255.0   # now values are near zero
```

**Fix**: Understand what each transform does and only normalize once.

---

## 12. Using Training Augmentation at Inference Time

**Pitfall**: Applying random crops, flips, or color jitter during validation/test changes the input distribution and makes evaluation unreliable.

**Fix**: Use deterministic preprocessing for inference.

```python
train_transform = T.Compose([T.RandomResizedCrop(224), T.RandomHorizontalFlip(), T.ToTensor(), T.Normalize(...)])
val_transform = T.Compose([T.Resize(256), T.CenterCrop(224), T.ToTensor(), T.Normalize(...)])
```

---

## 13. cv2.imshow Without cv2.waitKey

**Pitfall**: On some platforms, `cv2.imshow` will not render or will hang without `cv2.waitKey`.

**Fix**: Always pair `imshow` with `waitKey`.

```python
cv2.imshow("image", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

---

## 14. Destroying Windows Too Early

**Pitfall**: Calling `cv2.destroyAllWindows()` immediately after `waitKey(1)` in a loop can close windows before they render.

**Fix**: Release resources after the loop exits.

```python
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("video", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
```

---

## 15. Not Handling Empty Contours

**Pitfall**: `cv2.findContours` may return an empty list. Computing moments or bounding boxes on an empty contour crashes.

```python
M = cv2.moments(contours[0])
cx = int(M["m10"] / M["m00"])   # ZeroDivisionError if contour is empty
```

**Fix**: Check `m00` or contour length.

```python
for cnt in contours:
    if len(cnt) == 0:
        continue
    M = cv2.moments(cnt)
    if M["m00"] == 0:
        continue
    cx = int(M["m10"] / M["m00"])
```

---

## 16. Threshold Values on Float Images

**Pitfall**: Passing a float image in `[0, 1]` to `cv2.threshold` with threshold `127` will make the image entirely white or black.

**Fix**: Match threshold to value range.

```python
_, binary = cv2.threshold((img * 255).astype(np.uint8), 127, 255, cv2.THRESH_BINARY)
# or
_, binary = cv2.threshold(img, 0.5, 1.0, cv2.THRESH_BINARY)
```

---

## 17. Wrong `findContours` Return Signature

**Pitfall**: OpenCV 3 and 4 return `(contours, hierarchy)`, while OpenCV 2 returned `(image, contours, hierarchy)`. Code written for one version fails on another.

**Fix**: Use a robust unpacking.

```python
result = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = result[0] if len(result) == 2 else result[1]
```

---

## 18. Gaussian Blur Kernel Not Odd

**Pitfall**: `cv2.GaussianBlur` and `cv2.medianBlur` require odd kernel sizes. Passing an even size raises an error.

**Fix**: Ensure odd size.

```python
k = 5
blurred = cv2.GaussianBlur(img, (k, k), 0)
```

---

## 19. Negative Coordinates in Crop

**Pitfall**: Slicing with negative indices in NumPy wraps around instead of padding.

```python
patch = img[-10:10, -10:10]   # wraps from the end
```

**Fix**: Clamp coordinates or use `cv2.copyMakeBorder`.

---

## 20. Loading 16-Bit Images as 8-Bit

**Pitfall**: Medical or raw images may be 16-bit. Loading with default flags clips or scales incorrectly.

**Fix**: Use `cv2.IMREAD_ANYDEPTH` and handle scaling.

```python
img = cv2.imread("16bit.png", cv2.IMREAD_ANYDEPTH)
img_8bit = np.clip(img / 256, 0, 255).astype(np.uint8)
```

---

## 21. Decompression Bombs

**Pitfall**: Malicious images can decompress to enormous pixel arrays and crash the process.

**Fix**: Pillow has `Image.MAX_IMAGE_PIXELS`. Do not disable it without reason. Validate dimensions after loading.

```python
from PIL import Image
Image.MAX_IMAGE_PIXELS = None   # DANGEROUS
```

For OpenCV, check dimensions after `imread` and reject unexpectedly large images.

---

## 22. Trusting Filename Extensions

**Pitfall**: A file named `.jpg` may actually be a PNG, SVG, or executable. Relying on the extension for format decisions is unsafe.

**Fix**: Inspect file content or let the library detect the format.

```python
from PIL import Image
with Image.open(path) as im:
    print(im.format)   # actual format
```

---

## 23. Ignoring Channel Order on Save

**Pitfall**: Saving an RGB array with `cv2.imwrite` writes it as BGR because OpenCV interprets the array as BGR.

```python
img_rgb = np.zeros((100, 100, 3), dtype=np.uint8)
img_rgb[:, :, 0] = 255   # red channel in RGB
cv2.imwrite("red.jpg", img_rgb)   # saved as blue
```

**Fix**: Convert before saving.

```python
cv2.imwrite("red.jpg", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
```

---

## 24. Not Clipping After Float Operations

**Pitfall**: Float arithmetic can produce values outside `[0, 1]` or `[0, 255]`. Casting directly to `uint8` causes wrap-around.

```python
bright = (img.astype(float) * 1.5).astype(np.uint8)   # overflow
```

**Fix**: Clip before casting.

```python
bright = np.clip(img.astype(float) * 1.5, 0, 255).astype(np.uint8)
```

---

## 25. Resizing with Default Interpolation

**Pitfall**: `cv2.resize` defaults to bilinear interpolation, which is not always ideal. Downscaling with bilinear can introduce aliasing; upscaling can be soft.

**Fix**: Choose interpolation intentionally.

```python
down = cv2.resize(img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
up = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
```

---

## 26. Forgetting to Release VideoCapture

**Pitfall**: Not releasing `VideoCapture` can leave camera or file handles open.

**Fix**: Use context managers or explicit `release()`.

```python
cap = cv2.VideoCapture(0)
try:
    ret, frame = cap.read()
finally:
    cap.release()
```

---

## 27. Video Writer FourCC Mismatch

**Pitfall**: Using a FourCC codec that OpenCV was not built with causes the output file to be empty or corrupt.

**Fix**: Test available codecs. `mp4v` and `MJPG` are widely supported.

```python
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
```

---

## 28. Not Setting Random Seeds

**Pitfall**: Random augmentations, weight initialization, and data shuffling produce non-reproducible results.

**Fix**: Set all relevant seeds.

```python
import random, numpy as np, torch
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)
```

---

## 29. Data Leakage Between Splits

**Pitfall**: Splitting by filename prefix or time can accidentally put near-duplicates in both train and test sets.

**Fix**: Use group-aware splits or deduplicate before splitting.

---

## 30. Using `img.show()` in Production

**Pitfall**: `PIL.Image.show()` creates temporary files and invokes an external viewer. It blocks and is unsuitable for servers.

**Fix**: Save to disk or stream bytes; use matplotlib only in notebooks/development.

---

## 31. Confusing PIL `size` and NumPy `shape`

**Pitfall**: Pillow's `size` is `(width, height)`; NumPy's `shape` is `(height, width)`.

```python
im = Image.open("photo.jpg")
arr = np.array(im)
print(im.size)    # (w, h)
print(arr.shape)  # (h, w, c)
```

**Fix**: Be explicit about which convention you are using.

---

## 32. Not Converting PIL Modes Before NumPy

**Pitfall**: Converting a palette-mode image (`P`) directly to a NumPy array gives indices, not colors.

**Fix**: Convert to RGB or L first.

```python
arr = np.array(im.convert("RGB"))
```

---

## 33. Ignoring Gamma Correction

**Pitfall**: Blending or resizing images in gamma-encoded space produces darker edges and incorrect colors.

**Fix**: For physically correct operations, convert to linear light first.

```python
linear = np.power(img.astype(float) / 255.0, 2.2)
# operate in linear space
result = np.power(linear, 1.0 / 2.2) * 255
```

---

## 34. Hard-Coding Input Sizes

**Pitfall**: Models expect fixed input sizes. Passing the wrong size produces shape errors or silently wrong outputs.

**Fix**: Read input size from model config.

```python
input_size = model.config.image_size
```

---

## 35. Assuming All Images Have 3 Channels

**Pitfall**: Grayscale, RGBA, or CMYK images break code that assumes 3 channels.

**Fix**: Normalize channel count at load time.

```python
if img.ndim == 2:
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
elif img.shape[2] == 4:
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
```

---

## 36. Not Checking Tensor Value Range

**Pitfall**: PyTorch `ToTensor()` scales PIL images to `[0, 1]`. Some models expect `[-1, 1]` or raw `[0, 255]`.

**Fix**: Match the model's documented preprocessing.

---

## 37. Saving Batch Tensors Directly

**Pitfall**: Saving a PyTorch tensor of shape `(B, C, H, W)` as an image fails because image formats expect `(H, W, C)`.

**Fix**: Permute and select a single sample.

```python
img = tensor[0].permute(1, 2, 0).cpu().numpy()
```

---

## 38. Using Global State in OpenCV

**Pitfall**: `cv2.namedWindow`, `setMouseCallback`, and trackbars share global state. Multiple threads or contexts can interfere.

**Fix**: Keep GUI code isolated and single-threaded.

---

## 39. Not Scaling Canny Thresholds

**Pitfall**: Fixed Canny thresholds work poorly across different lighting conditions.

**Fix**: Use percentile-based thresholds or adaptive methods.

```python
median = np.median(gray)
lower = int(max(0, 0.66 * median))
upper = int(min(255, 1.33 * median))
edges = cv2.Canny(gray, lower, upper)
```

---

## 40. Connected Components on Wrong Data Type

**Pitfall**: `cv2.connectedComponents` expects a binary `uint8` image. Passing a boolean or `int32` array may fail.

**Fix**: Cast explicitly.

```python
labels, stats = cv2.connectedComponents(np.uint8(binary_mask) * 255)
```

---

## 41. Feature Matching Without Ratio Test

**Pitfall**: Using all matches from `knnMatch` includes many false correspondences.

**Fix**: Apply Lowe's ratio test.

```python
good = []
for m, n in matches:
    if m.distance < 0.75 * n.distance:
        good.append(m)
```

---

## 42. Homography with Too Few Matches

**Pitfall**: `cv2.findHomography` needs at least 4 matches. Fewer matches raise an error or produce garbage.

**Fix**: Check match count before calling.

```python
if len(good) < 4:
    raise ValueError("Not enough matches")
```

---

## 43. Not Handling Empty Video Files

**Pitfall**: `VideoCapture` on a corrupt file may open successfully but return no frames.

**Fix**: Check `isOpened()` and that the first frame reads.

```python
cap = cv2.VideoCapture(path)
if not cap.isOpened():
    raise IOError("Cannot open video")
ret, frame = cap.read()
if not ret:
    raise IOError("Video has no frames")
```

---

## 44. Wrong Order in PyTorch Normalize

**Pitfall**: `torchvision.transforms.Normalize` subtracts mean then divides by std. Some frameworks divide by std first.

**Fix**: Use the exact normalization recipe from the model's training setup.

---

## 45. Ignoring Class Imbalance in Segmentation

**Pitfall**: Training a segmentation model with a dominant background class produces near-zero gradients for rare classes.

**Fix**: Use class weights, focal loss, or Lovász-Softmax.

---

## 46. Augmenting Validation Data

**Pitfall**: Random augmentations during validation produce inconsistent metrics.

**Fix**: Disable randomness for validation.

```python
model.eval()
with torch.no_grad():
    for inputs, labels in val_loader:
        ...
```

---

## 47. Not Freezing BatchNorm in Transfer Learning

**Pitfall**: When fine-tuning with small batch sizes, updating BatchNorm statistics can destabilize training.

**Fix**: Set BatchNorm layers to eval mode or use `model.eval()` on the backbone during initial fine-tuning.

---

## 48. Saving Models Instead of State Dicts

**Pitfall**: `torch.save(model, path)` pickles the entire model object, which breaks if class definitions change.

**Fix**: Save state dicts.

```python
torch.save(model.state_dict(), "model.pth")
model.load_state_dict(torch.load("model.pth"))
```

---

## 49. Wrong Device for Inference

**Pitfall**: Sending input to CPU while the model is on GPU (or vice versa) raises device mismatch errors.

**Fix**: Move both to the same device.

```python
inputs = inputs.to(device)
model = model.to(device)
```

---

## 50. Not Enabling Eval Mode

**Pitfall**: Forgetting `model.eval()` leaves dropout and BatchNorm in training mode, causing inconsistent inference results.

**Fix**:

```python
model.eval()
with torch.no_grad():
    outputs = model(inputs)
```

---

## 51. Memory Leaks in DataLoader

**Pitfall**: Creating a `DataLoader` inside a loop without deleting it can accumulate workers and memory.

**Fix**: Reuse loaders or explicitly delete them.

---

## 52. Not Using `pin_memory`

**Pitfall**: Without `pin_memory=True`, CPU-to-GPU transfers are slower.

**Fix**: Use `pin_memory=True` when training on GPU.

---

## 53. Large Batch Size OOM

**Pitfall**: A batch that fits in CPU memory may OOM on GPU.

**Fix**: Reduce batch size, use gradient accumulation, or mixed precision.

---

## 54. Forgetting to Zero Gradients

**Pitfall**: Accumulating gradients across iterations without zeroing causes incorrect updates.

**Fix**:

```python
optimizer.zero_grad()
loss.backward()
optimizer.step()
```

---

## 55. Loading Checkpoints on Different Devices

**Pitfall**: `torch.load` on a CPU machine for a checkpoint saved on GPU fails.

**Fix**: Use `map_location`.

```python
checkpoint = torch.load("model.pth", map_location="cpu")
```

---

## 56. Not Handling `nan` Loss

**Pitfall**: `nan` loss can propagate and corrupt weights.

**Fix**: Detect and investigate.

```python
if torch.isnan(loss):
    print("NaN loss detected")
    break
```

---

## 57. Ignoring Learning Rate Warmup

**Pitfall**: Starting training with a large learning rate can cause divergence.

**Fix**: Use warmup for the first few epochs.

---

## 58. Using Sigmoid with CrossEntropyLoss

**Pitfall**: `CrossEntropyLoss` expects raw logits. Passing sigmoid or softmax outputs produces wrong gradients.

**Fix**: Pass logits directly.

```python
loss = criterion(outputs, labels)   # outputs are logits
```

---

## 59. Wrong Loss for Multi-Label

**Pitfall**: Using `CrossEntropyLoss` for multi-label classification is incorrect.

**Fix**: Use `BCEWithLogitsLoss` for multi-label.

---

## 60. Not Monitoring Validation Metric

**Pitfall**: Training loss can decrease while validation metric degrades (overfitting).

**Fix**: Track validation metrics and use early stopping.

---

## 61. Production Input Assumptions

**Pitfall**: Production images may differ from training (different resolution, compression, color space, orientation).

**Fix**: Validate and normalize inputs in the serving layer.

---

## 62. Ignoring Latency Requirements

**Pitfall**: A model that works offline may be too slow for real-time use.

**Fix**: Profile end-to-end latency, optimize with TensorRT/ONNX, and set a target FPS.

---

## 63. Hard-Coded Paths

**Pitfall**: Hard-coded file paths break when the code runs in a different environment.

**Fix**: Use configuration files or environment variables.

---

## 64. Not Versioning Preprocessing

**Pitfall**: Changing preprocessing after training without versioning causes train/serve skew.

**Fix**: Save preprocessing config alongside the model checkpoint.

---

## 65. Ignoring Privacy in EXIF

**Pitfall**: EXIF metadata can contain GPS coordinates and camera serial numbers.

**Fix**: Strip metadata before sharing images.

```python
from PIL import Image
with Image.open(path) as im:
    im.save("out.jpg", exif=b"")
```

---

## 66. Trusting Bounding Box Annotations

**Pitfall**: Annotated boxes may be out of bounds, zero-area, or mislabeled.

**Fix**: Validate annotations during dataset creation.

```python
def valid_box(box, w, h):
    x1, y1, x2, y2 = box
    return 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h
```

---

## 67. Using `float64` Unnecessarily

**Pitfall**: `float64` arrays use twice the memory of `float32` and are slower on GPUs.

**Fix**: Convert to `float32` for deep learning.

---

## 68. Not Handling Multi-Frame Formats

**Pitfall**: TIFF, GIF, and MPO files may contain multiple frames. `Image.open` loads only the first by default.

**Fix**: Iterate frames explicitly.

```python
with Image.open(path) as im:
    for i in range(im.n_frames):
        im.seek(i)
        im.save(f"frame_{i}.png")
```

---

## 69. Saving Over the Original File

**Pitfall**: Saving back to the same path with a lossy format corrupts the original.

**Fix**: Save to a new file or a different format.

---

## 70. Not Checking `cv2.VideoWriter.isOpened`

**Pitfall**: If the codec or path is invalid, `VideoWriter` silently fails.

**Fix**: Check after creation.

```python
writer = cv2.VideoWriter(path, fourcc, fps, size)
if not writer.isOpened():
    raise IOError("Failed to open video writer")
```

---

## 71. Assuming Square Pixels

**Pitfall**: Some images (e.g., anamorphic video) have non-square pixel aspect ratios.

**Fix**: Read pixel aspect ratio from metadata and resample if needed.

---

## 72. Wrong `cv2.fillPoly` Input Shape

**Pitfall**: `cv2.fillPoly` expects a list of arrays with shape `(N, 1, 2)`.

**Fix**: Reshape points.

```python
pts = np.array([[10, 10], [100, 10], [100, 100]], np.int32)
pts = pts.reshape((-1, 1, 2))
cv2.fillPoly(img, [pts], (255, 0, 0))
```

---

## 73. Not Resizing Annotations with Images

**Pitfall**: When resizing an image, bounding boxes, masks, and keypoints must be scaled by the same factor.

**Fix**: Store and apply the scale factor.

```python
scale_x = new_w / old_w
scale_y = new_h / old_h
new_box = [x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]
```

---

## 74. Confusing `cv2.warpAffine` and `cv2.warpPerspective`

**Pitfall**: Using a 2x3 affine matrix with `warpPerspective` (which expects 3x3) raises a dimension error.

**Fix**: Match the matrix to the function.

---

## 75. Not Handling Transparent Backgrounds

**Pitfall**: Compositing an RGBA image over RGB without handling alpha produces black fringes.

**Fix**: Composite over a background or premultiply alpha.

---

## 76. Using `plt.imshow` on Float Images Without Range

**Pitfall**: `plt.imshow` normalizes float images per call. The same array can look different across plots.

**Fix**: Specify `vmin` and `vmax`.

```python
plt.imshow(gray, cmap="gray", vmin=0, vmax=255)
```

---

## 77. Not Casting Before Display

**Pitfall**: Displaying a `float64` image with values in `[0, 1]` may appear black if the viewer expects `[0, 255]`.

**Fix**: Scale to the expected range.

---

## 78. Ignoring `copyMakeBorder` Value Type

**Pitfall**: The `value` argument to `cv2.copyMakeBorder` must match the image dtype. A float tuple on a `uint8` image causes a type error.

**Fix**: Use integer tuples for `uint8` images.

---

## 79. Not Closing imageio Readers

**Pitfall**: `imageio` readers can hold file handles.

**Fix**: Use context managers.

```python
import imageio.v3 as iio
with iio.imopen(path, "r") as f:
    meta = f.metadata()
```

---

## 80. Forgetting `torch.no_grad()` During Inference

**Pitfall**: Without `torch.no_grad()`, PyTorch builds the computation graph and wastes memory.

**Fix**: Wrap inference.

```python
with torch.no_grad():
    outputs = model(inputs)
```

---

## 81. Summary of Avoidance Strategies

- Always validate loaded images.
- Be explicit about color space, shape, and dtype conventions.
- Clip and cast carefully after arithmetic.
- Use nearest-neighbor for masks and labels.
- Separate training and inference preprocessing.
- Check OpenCV return values and handle empty results.
- Set seeds for reproducibility.
- Profile memory and latency early.
- Sanitize production inputs.
- Version preprocessing with models.
- Validate annotations and metadata.
- Use context managers and release resources.


## 82. Additional OpenCV Pitfalls

### 82.1 `cv2.imread` with Non-ASCII Paths

On some systems, `cv2.imread` fails with paths containing non-ASCII characters. OpenCV's C++ layer may not handle Unicode paths correctly on all platforms.

**Fix**: Read the file as bytes and decode with `cv2.imdecode`.

```python
import numpy as np
import cv2

with open(path, "rb") as f:
    bytes_data = f.read()
arr = np.frombuffer(bytes_data, dtype=np.uint8)
img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
```

### 82.2 `cv2.imwrite` Fails Silently

`cv2.imwrite` returns `True` or `False`, but it does not raise an exception on failure. Directory missing or invalid matrix can cause failures.

**Fix**: Check the return value and ensure the output directory exists.

```python
from pathlib import Path
Path(out_path).parent.mkdir(parents=True, exist_ok=True)
ok = cv2.imwrite(str(out_path), img)
if not ok:
    raise IOError(f"Failed to write {out_path}")
```

### 82.3 `cv2.findContours` Modifies Source Image

In older OpenCV versions, `findContours` modifies the source binary image. In OpenCV 4, it does not modify the source when using the new return signature, but this remains a common source of confusion.

**Fix**: Pass a copy if you need the original mask.

```python
contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

### 82.4 `cv2.cvtColor` Fails on Grayscale

Calling `cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)` on a 2-D array raises an error because the image is already grayscale.

**Fix**: Check dimensions first.

```python
if img.ndim == 3:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
else:
    gray = img
```

### 82.5 `cv2.imshow` in Jupyter

`cv2.imshow` often does not work inside Jupyter notebooks or remote servers because it requires a local display server.

**Fix**: Use matplotlib in notebooks, or save images and display with IPython.display.

### 82.6 `cv2.VideoCapture` Set Order

Setting `CAP_PROP_FRAME_WIDTH` and `CAP_PROP_FRAME_HEIGHT` before `CAP_PROP_FPS` may fail on some backends.

**Fix**: Set properties in the order recommended by the backend, or query actual values after setting.

### 82.7 `cv2.addWeighted` Type Mismatch

Both images must have the same size and number of channels. Floating-point images need matching dtypes.

**Fix**: Convert to a common format before blending.

---

## 83. Additional Pillow Pitfalls

### 83.1 `Image.thumbnail` Modifies In-Place

`thumbnail()` resizes the image in place and preserves aspect ratio. It does not return a new image of the exact requested size.

**Fix**: Use `resize()` for exact dimensions, or copy before thumbnailing.

```python
thumb = im.copy()
thumb.thumbnail((128, 128))
```

### 83.2 `Image.rotate` Default Fill Color

`rotate()` fills uncovered areas with black by default.

**Fix**: Set `expand=True` to fit the whole rotated image, or specify `fillcolor`.

```python
rotated = im.rotate(45, expand=True, fillcolor=(255, 255, 255))
```

### 83.3 `Image.resize` vs `reduce`

`reduce()` downsamples by integer factors and is faster for large reductions, but `resize()` is more flexible.

**Fix**: Use `reduce()` for power-of-two downscaling, `resize()` for arbitrary sizes.

### 83.4 `Image.crop` Returns Copy

`crop()` returns a copy, but prior to Pillow 3.4 it was lazy. This is no longer an issue in modern Pillow.

### 83.5 `Image.save` Ignores Unknown Options

Pillow silently ignores format-specific options it does not recognize. For example, `quality` has no effect on PNG.

**Fix**: Use the correct options for each format.

### 83.6 GIF Palette Limitations

GIF only supports 256 colors per frame. Saving a full-color image as GIF triggers color quantization and may look posterized.

**Fix**: Quantize explicitly if you need control, or use PNG/WebP for full color.

---

## 84. NumPy Pitfalls

### 84.1 Transpose vs. Permute

`np.transpose` reorders axes. Confusing `(H, W, C)` with `(C, H, W)` is common.

```python
# HWC to CHW
chw = np.transpose(hw, (2, 0, 1))
```

### 84.2 Boolean Indexing Returns Copy

Assigning through a boolean mask modifies the original array, but the selected values themselves are a copy.

### 84.3 Slicing Returns View

Slicing with basic indexing returns a view. Advanced indexing returns a copy.

```python
view = img[::2, ::2]     # view
copy = img[[0, 1], [0, 1]]   # copy
```

### 84.4 dtype Promotion

NumPy promotes `uint8` and `int16` to `int16` in some operations. Be aware of intermediate types.

### 84.5 `np.uint8` Negative Values

Negative `uint8` wraps to large positive values.

```python
x = np.array([0], dtype=np.uint8)
print(x - 1)   # [255]
```

**Fix**: Cast before subtraction or use `np.subtract` with `casting='unsafe'` and clip.

---

## 85. Deep Learning Preprocessing Pitfalls

### 85.1 Different Normalization for Pretrained Models

ImageNet models use mean `[0.485, 0.456, 0.406]` and std `[0.229, 0.224, 0.225]`. Models trained on CIFAR or custom datasets may use different normalization.

**Fix**: Use the normalization recipe from the model's source.

### 85.2 Forgetting `ToTensor` Scaling

`ToTensor` scales PIL images from `[0, 255]` to `[0, 1]`. If you manually normalize `uint8` values, you divide by 255 twice.

### 85.3 Random Crop Exceeds Image Size

`RandomResizedCrop` can fail on very small images. `RandomCrop` raises an error if the crop is larger than the image.

**Fix**: Resize or pad small images first.

### 85.4 Albumentations Channel Order

Albumentations expects RGB NumPy arrays. Passing BGR arrays leads to incorrect color augmentations.

### 85.5 torchvision v2 vs v1

`torchvision.transforms.v2` supports images, masks, bounding boxes, and labels in a single transform call. Mixing v1 and v2 transforms can cause unexpected behavior.

**Fix**: Use v2 consistently for new projects.

---

## 86. Object Detection Pitfalls

### 86.1 Bounding Box Format Mismatch

Models expect specific formats: COCO uses `xywh`, Pascal VOC uses `xyxy`, YOLO uses normalized `cxcywh`.

**Fix**: Convert explicitly and validate.

### 86.2 NMS Before Confidence Threshold

Running NMS on all detections including very low-confidence ones is inefficient and can produce noisy results.

**Fix**: Filter by confidence first, then apply NMS.

### 86.3 Ignoring Image Border Boxes

Boxes that touch the image border may be truncated or invalid after augmentation.

**Fix**: Clip boxes to image bounds after transforms.

### 86.4 Anchor Size Mismatch

Using anchors that are too large or too small for the object sizes in your dataset degrades detection performance.

**Fix**: Compute anchor sizes from your dataset or use anchor-free detectors.

---

## 87. Segmentation Pitfalls

### 87.1 Class Imbalance

Background pixels often dominate. The model may learn to predict background everywhere.

**Fix**: Use class weights, focal loss, or balanced sampling.

### 87.2 Wrong Loss Function

Using `CrossEntropyLoss` with one-hot encoded masks instead of class indices.

**Fix**: Pass integer class indices to `CrossEntropyLoss`.

### 87.3 Ignoring Void Labels

Some datasets mark ambiguous pixels with a void/ignore label. Including them in loss computation hurts training.

**Fix**: Mask out void pixels in the loss.

### 87.4 Mask Resizing Artifacts

Nearest-neighbor resizing can produce aliased edges. For evaluation, resize predictions to original size, not labels to model size.

---

## 88. Video Processing Pitfalls

### 88.1 Frame Dropping

Reading frames faster than the decoder can provide causes dropped frames.

**Fix**: Process frames at the video's frame rate or use a dedicated capture thread.

### 88.2 Seeking Accuracy

`cv2.VideoCapture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)` is not frame-accurate for all codecs.

**Fix**: Use keyframe-aware seeking or re-encode with an all-intra codec.

### 88.3 Audio Sync

OpenCV does not handle audio. Synchronizing audio with processed video requires FFmpeg or similar.

### 88.4 Variable Frame Rate

Some videos have variable frame rate. FPS queries return an average.

**Fix**: Use FFmpeg for frame-exact processing if timing matters.

---

## 89. Camera Calibration Pitfalls

### 89.1 Insufficient Chessboard Images

Calibration needs many images covering the entire field of view and various angles.

**Fix**: Capture 15-30 high-quality calibration images.

### 89.2 Poor Lighting on Calibration Target

Glare or shadows on the checkerboard reduce corner detection accuracy.

**Fix**: Use diffuse, even lighting.

### 89.3 Wrong Checkerboard Inner Corners

`findChessboardCorners` expects the number of inner corners, not squares.

**Fix**: A 9x6 checkerboard has 8x5 inner corners.

---

## 90. Feature Matching Pitfalls

### 90.1 ORB with Float Images

ORB expects `uint8` grayscale images.

**Fix**: Convert and cast before detection.

### 90.2 SIFT Patent Issues

SIFT and SURF are patented. They are available in `opencv-contrib-python` but not in the base `opencv-python` package in some builds.

**Fix**: Use ORB for free alternatives, or verify SIFT availability.

### 90.3 Too Many Features

Detecting thousands of features slows matching without improving accuracy.

**Fix**: Limit features with `nfeatures` and apply ratio test.

---

## 91. Augmentation Pitfalls

### 91.1 Extreme Augmentation

Over-augmenting can make images unrecognizable and hurt convergence.

**Fix**: Monitor augmented samples and keep augmentations realistic.

### 91.2 Inconsistent Augmentation for Siamese Networks

Siamese and contrastive learning require different augmentations per view. Applying the same transform to both views defeats the purpose.

### 91.3 Normalization Before Augmentation

Normalizing to zero mean before color jitter makes jitter mathematically incorrect.

**Fix**: Apply photometric augmentations on `[0, 1]` or `[0, 255]` images, then normalize.

---

## 92. Dataset Pitfalls

### 92.1 Train/Test From Same Source

Images from the same photoshoot or video sequence may appear in both splits, causing over-optimistic metrics.

**Fix**: Split by group (e.g., person ID, scene, video).

### 92.2 Label Noise

Incorrect labels reduce model performance.

**Fix**: Clean labels, use confident learning, or train with label smoothing.

### 92.3 Small Validation Set

A tiny validation set gives noisy metric estimates.

**Fix**: Use cross-validation or a larger validation set.

---

## 93. Evaluation Pitfalls

### 93.1 Metric Selection

Accuracy is misleading for imbalanced classes. Use balanced accuracy, F1, or AUC.

### 93.2 Threshold Selection

Using a default 0.5 threshold may not be optimal. Tune the threshold on a validation set.

### 93.3 Comparing Across Preprocessing

Metrics are not comparable if preprocessing differs.

**Fix**: Fix preprocessing and report it clearly.

---

## 94. Deployment Pitfalls

### 94.1 Train/Serve Skew

Inference preprocessing differs from training preprocessing.

**Fix**: Use the exact same preprocessing code and config.

### 94.2 Batch Size Assumptions

Model exported with batch size 1 may fail with larger batches if shapes are hard-coded.

**Fix**: Use dynamic axes in ONNX or batch dimension `-1`.

### 94.3 Missing Fallbacks

Production requests may include unsupported formats or sizes.

**Fix**: Return a graceful error and log the input.

---

## 95. Security Pitfalls

### 95.1 Arbitrary File Uploads

Allowing users to upload any image file can lead to stored XSS, decompression bombs, or remote code execution if the decoder has vulnerabilities.

**Fix**: Validate file size, dimensions, and format; sandbox image decoding.

### 95.2 EXIF Data Leakage

EXIF can contain GPS coordinates and device identifiers.

**Fix**: Strip metadata before public release.

### 95.3 Pickled Models

Loading untrusted `.pth` or `.pkl` files can execute arbitrary code.

**Fix**: Only load models from trusted sources; prefer state dicts or ONNX.

---

## 96. Performance Pitfalls

### 96.1 Python Loops Over Pixels

Looping over every pixel in Python is orders of magnitude slower than vectorized operations.

**Fix**: Use NumPy, OpenCV, or Cython.

### 96.2 Loading Full Dataset into Memory

Loading all images into RAM does not scale.

**Fix**: Use lazy loading and DataLoader workers.

### 96.3 Unnecessary Copies

Each copy of a large image uses memory. Use views when possible.

### 96.4 Not Pinning Memory

For GPU training, `pin_memory=True` significantly reduces CPU-to-GPU transfer time.

### 96.5 Too Many DataLoader Workers

More workers than CPU cores can slow data loading due to contention.

**Fix**: Set `num_workers` to the number of CPU cores or less.

---

## 97. Environment Pitfalls

### 97.1 Conflicting OpenCV Packages

Installing both `opencv-python` and `opencv-python-headless` can cause import errors.

**Fix**: Use only one.

### 97.2 Missing GUI Backend

Headless servers lack display libraries needed for `cv2.imshow`.

**Fix**: Install headless OpenCV or avoid GUI functions.

### 97.3 CUDA Version Mismatch

PyTorch / TensorFlow CUDA versions must match the installed NVIDIA driver and toolkit.

**Fix**: Use conda/pip packages with the correct CUDA version.

---

## 98. Reproducibility Pitfalls

### 98.1 Different Random Seed Behavior Across Devices

CUDA operations may not be deterministic across different GPU architectures.

**Fix**: Accept small numerical differences; test on the target device.

### 98.2 Undocumented Hyperparameters

Forgetting to record learning rate, batch size, or augmentation settings makes experiments impossible to reproduce.

**Fix**: Log all hyperparameters with MLflow, Weights & Biases, or TensorBoard.

---

## 99. Common Error Messages and Fixes

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| `cv2.error: OpenCV(...) -215:Assertion failed` | Incorrect image shape, type, or parameters | Check dtype, channels, and sizes |
| `cannot identify image file` | Corrupt or non-image file | Validate file type |
| `ValueError: could not broadcast input array` | Shape mismatch in assignment | Verify shapes before assignment |
| `RuntimeError: Expected all tensors to be on the same device` | Model and input on different devices | Move both to same device |
| `CUDA out of memory` | Batch too large or memory leak | Reduce batch, clear cache, use mixed precision |
| `KeyError: 'input'` | Wrong ONNX input name | Print `session.get_inputs()` |

---

## 100. Final Pitfall Checklist

Before shipping vision code, verify:

- [ ] Color space is correct at every library boundary.
- [ ] Image loads are checked for `None` or exceptions.
- [ ] EXIF orientation is handled.
- [ ] Masks use nearest-neighbor resize.
- [ ] Augmentation is training-only.
- [ ] Normalization matches the model.
- [ ] Bounding boxes are validated and clipped.
- [ ] Random seeds are set.
- [ ] Resources (VideoCapture, writers, windows) are released.
- [ ] Production inputs are sanitized.
- [ ] Metadata is stripped if privacy matters.
- [ ] Model is in eval mode for inference.
- [ ] Latency and memory are profiled.
- [ ] Preprocessing config is versioned with the model.
