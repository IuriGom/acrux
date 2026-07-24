# Vision: Idiomatic Patterns and Reusable Recipes

This file collects practical patterns, best-practice recipes, design patterns, and reusable code templates for image processing and computer vision in Python.

---

## 1. Safe Image Loading Pattern

Always validate that an image loaded successfully and normalize it to a known state (dtype, color space, dimensions) before further processing.

```python
import cv2
import numpy as np
from pathlib import Path

def load_image(path, color_space="rgb", target_dtype=np.uint8):
    """
    Load an image robustly and normalize it.

    Args:
        path: file path (str or Path).
        color_space: "rgb", "bgr", "gray", or "unchanged".
        target_dtype: np.uint8 or np.float32.

    Returns:
        NumPy array in the requested color space and dtype.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    flag = cv2.IMREAD_UNCHANGED
    if color_space == "gray":
        flag = cv2.IMREAD_GRAYSCALE
    elif color_space in ("rgb", "bgr"):
        flag = cv2.IMREAD_COLOR

    img = cv2.imread(str(path), flag)
    if img is None:
        raise ValueError(f"cv2.imread could not decode: {path}")

    if color_space == "rgb" and img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if target_dtype == np.float32:
        img = img.astype(np.float32) / 255.0

    return img
```

**Why this pattern matters**: OpenCV returns `None` silently on failure. Many downstream operations will fail with confusing errors if you do not check.

---

## 2. Lazy Pillow Loading with Context Manager

Pillow's `Image.open()` is lazy and keeps a file handle open. Use a context manager or explicit `.load()` to avoid file-handle leaks and closed-image errors.

```python
from PIL import Image
from pathlib import Path

def load_pil_image(path, mode="RGB", apply_exif=True):
    path = Path(path)
    with Image.open(path) as im:
        if apply_exif:
            from PIL import ImageOps
            im = ImageOps.exif_transpose(im)
        if mode:
            im = im.convert(mode)
        return im.copy()
```

`im.copy()` forces the pixel data into memory and closes the dependency on the original file.

---

## 3. Aspect-Preserving Resize

Distorting aspect ratio changes the semantics of objects. Resize so the largest dimension fits a target size, then optionally pad to a square.

```python
import cv2
import numpy as np

def resize_keep_aspect(image, max_size, interpolation=cv2.INTER_AREA):
    """Resize so neither dimension exceeds max_size."""
    h, w = image.shape[:2]
    scale = min(max_size / h, max_size / w, 1.0)
    if scale == 1.0:
        return image
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=interpolation)


def letterbox(image, target_size, fill=(128, 128, 128)):
    """Resize with aspect ratio preserved and pad to target_size x target_size."""
    h, w = image.shape[:2]
    scale = min(target_size / h, target_size / w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    top = (target_size - new_h) // 2
    bottom = target_size - new_h - top
    left = (target_size - new_w) // 2
    right = target_size - new_w - left

    return cv2.copyMakeBorder(resized, top, bottom, left, right,
                              cv2.BORDER_CONSTANT, value=fill)
```

---

## 4. Universal Color-Space Normalizer

Centralize color-space conversion so downstream code never has to guess.

```python
import cv2
import numpy as np

def ensure_color_space(image, output_space="rgb", input_space="auto"):
    """
    Convert an image to the requested color space.
    If input_space is 'auto', assume RGB for 3-channel unless caller specifies.
    """
    if image.ndim == 2:
        if output_space == "gray":
            return image
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    if output_space == "gray":
        if image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY if input_space == "rgb" else cv2.COLOR_BGR2GRAY)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY if input_space == "rgb" else cv2.COLOR_BGRA2GRAY)

    if output_space in ("rgb", "bgr"):
        src = input_space
        dst = output_space
        if src == "auto":
            src = "rgb"
        if src == dst:
            return image
        if src == "rgb" and dst == "bgr":
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if src == "bgr" and dst == "rgb":
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if image.shape[2] == 4:
            if src == "rgba" and dst == "rgb":
                return cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            if src == "bgra" and dst == "bgr":
                return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    raise ValueError(f"Unsupported conversion {input_space} -> {output_space}")
```

---

## 5. Center Crop and Random Crop

```python
import numpy as np

def center_crop(image, crop_h, crop_w):
    h, w = image.shape[:2]
    top = (h - crop_h) // 2
    left = (w - crop_w) // 2
    return image[top:top + crop_h, left:left + crop_w]


def random_crop(image, crop_h, crop_w):
    h, w = image.shape[:2]
    if crop_h > h or crop_w > w:
        raise ValueError("Crop size larger than image")
    top = np.random.randint(0, h - crop_h + 1)
    left = np.random.randint(0, w - crop_w + 1)
    return image[top:top + crop_h, left:left + crop_w]
```

---

## 6. Preprocessing Pipeline as Callable Composition

Build preprocessing as small, pure, reusable callables and compose them.

```python
class Compose:
    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image):
        for t in self.transforms:
            image = t(image)
        return image


class Resize:
    def __init__(self, size):
        self.size = size

    def __call__(self, image):
        return cv2.resize(image, (self.size, self.size))


class Normalize:
    def __init__(self, mean, std):
        self.mean = np.array(mean)
        self.std = np.array(std)

    def __call__(self, image):
        return (image.astype(np.float32) / 255.0 - self.mean) / self.std


preprocess = Compose([
    Resize(224),
    Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
```

This pattern mirrors torchvision's `Compose` and makes pipelines easy to test and extend.

---

## 7. Train/Val Transform Split

Never apply random augmentations to validation or test data. Use a deterministic preprocessing path for inference.

```python
def build_transforms(input_size=224, is_training=True):
    from torchvision import transforms
    if is_training:
        return transforms.Compose([
            transforms.RandomResizedCrop(input_size, scale=(0.08, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(0.4, 0.4, 0.4, 0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
    return transforms.Compose([
        transforms.Resize(int(input_size * 1.14)),
        transforms.CenterCrop(input_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
```

---

## 8. Albumentations Pipeline for Object Detection

Spatial augmentations must be applied identically to images and bounding boxes.

```python
import albumentations as A
from albumentations.pytorch import ToTensorV2

train_transform = A.Compose([
    A.LongestMaxSize(max_size=640),
    A.PadIfNeeded(min_height=640, min_width=640, border_mode=cv2.BORDER_CONSTANT),
    A.HorizontalFlip(p=0.5),
    A.RandomBrightnessContrast(p=0.2),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
], bbox_params=A.BboxParams(format="pascal_voc", label_fields=["class_labels"]))

augmented = train_transform(image=img, bboxes=bboxes, class_labels=labels)
img_tensor = augmented["image"]
new_bboxes = augmented["bboxes"]
new_labels = augmented["class_labels"]
```

---

## 9. Segmentation Mask Augmentation

Masks must be transformed with nearest-neighbor interpolation to preserve class indices.

```python
import albumentations as A

transform = A.Compose([
    A.RandomResizedCrop(512, 512),
    A.HorizontalFlip(p=0.5),
], additional_targets={"mask": "mask"})

augmented = transform(image=img, mask=mask)
aug_img = augmented["image"]
aug_mask = augmented["mask"]
```

If using OpenCV directly for mask resize:

```python
resized_mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
```

---

## 10. Convert Between Library Representations

### 10.1 OpenCV -> Pillow

```python
from PIL import Image
import cv2

def cv2_to_pil(bgr_img):
    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)
```

### 10.2 Pillow -> OpenCV

```python
import numpy as np
import cv2

def pil_to_cv2(pil_img):
    rgb = np.array(pil_img)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
```

### 10.3 OpenCV -> PyTorch

```python
import torch

def cv2_to_tensor(bgr_img, normalize=True):
    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    if normalize:
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        tensor = (tensor - mean) / std
    return tensor
```

### 10.4 PyTorch -> OpenCV

```python
import torch
import numpy as np
import cv2

def tensor_to_cv2(tensor, denormalize=True):
    if denormalize:
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        tensor = tensor * std + mean
    img = tensor.detach().cpu().permute(1, 2, 0).numpy()
    img = np.clip(img * 255, 0, 255).astype(np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
```

---

## 11. Batch Image Processing

Process a directory of images in parallel while handling errors gracefully.

```python
from pathlib import Path
from PIL import Image, ImageOps
from joblib import Parallel, delayed
import traceback

def process_one(src_path, out_dir, size=(256, 256)):
    try:
        with Image.open(src_path) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail(size, Image.Resampling.LANCZOS)
            im = im.convert("RGB")
            out_path = Path(out_dir) / f"{src_path.stem}.jpg"
            im.save(out_path, quality=85, optimize=True)
        return (src_path.name, "ok")
    except Exception as e:
        return (src_path.name, f"error: {e}")

def batch_process(src_dir, out_dir, size=(256, 256), n_jobs=4):
    src_dir, out_dir = Path(src_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = list(src_dir.glob("*"))
    results = Parallel(n_jobs=n_jobs)(
        delayed(process_one)(p, out_dir, size) for p in paths
    )
    return results
```

---

## 12. Video Frame Extraction Pattern

Extract frames at a fixed interval for dataset creation or analysis.

```python
import cv2
from pathlib import Path

def extract_frames(video_path, out_dir, interval_sec=1.0):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval_frames = int(fps * interval_sec)
    frame_idx = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval_frames == 0:
            out_path = out_dir / f"{Path(video_path).stem}_{frame_idx:06d}.jpg"
            cv2.imwrite(str(out_path), frame)
            saved += 1
        frame_idx += 1

    cap.release()
    return saved
```

---

## 13. Video Writer Pattern

Always release the writer and verify the output file exists.

```python
import cv2
from pathlib import Path

def write_video(frames, out_path, fps=30, size=None, codec="mp4v"):
    if not frames:
        raise ValueError("No frames to write")
    if size is None:
        size = (frames[0].shape[1], frames[0].shape[0])

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, size)
    if not writer.isOpened():
        raise IOError(f"Could not open video writer for {out_path}")

    for frame in frames:
        if (frame.shape[1], frame.shape[0]) != size:
            frame = cv2.resize(frame, size)
        writer.write(frame)

    writer.release()
    if not Path(out_path).exists():
        raise IOError(f"Video file was not created: {out_path}")
```

---

## 14. Camera Capture Pattern

```python
import cv2

def capture_frame(device_index=0, width=None, height=None):
    cap = cv2.VideoCapture(device_index)
    if width and height:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Failed to capture frame")
    return frame
```

---

## 15. Template Matching Pattern

```python
import cv2
import numpy as np

def find_template(image, template, threshold=0.8, method=cv2.TM_CCOEFF_NORMED):
    result = cv2.matchTemplate(image, template, method)
    loc = np.where(result >= threshold)
    matches = []
    h, w = template.shape[:2]
    for pt in zip(*loc[::-1]):
        matches.append((pt[0], pt[1], pt[0] + w, pt[1] + h, result[pt[1], pt[0]]))
    return matches
```

For multiple overlapping matches, apply NMS.

---

## 16. Contour Analysis Pattern

```python
import cv2
import numpy as np

def analyze_contours(binary_mask):
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    objects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 100:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        perimeter = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * perimeter, True)
        M = cv2.moments(cnt)
        cx = int(M["m10"] / M["m00"]) if M["m00"] else x + w // 2
        cy = int(M["m01"] / M["m00"]) if M["m00"] else y + h // 2
        objects.append({
            "bbox": (x, y, w, h),
            "area": area,
            "perimeter": perimeter,
            "centroid": (cx, cy),
            "num_corners": len(approx),
            "contour": cnt,
        })
    return objects
```

---

## 17. Shape Classification Pattern

```python
def classify_shape(num_corners, aspect_ratio):
    if num_corners == 3:
        return "triangle"
    if num_corners == 4:
        return "square" if 0.95 <= aspect_ratio <= 1.05 else "rectangle"
    if num_corners == 5:
        return "pentagon"
    if num_corners == 6:
        return "hexagon"
    if num_corners > 6:
        return "circle"
    return "unknown"
```

---

## 18. Document Scanning Pattern

```python
import cv2
import numpy as np

def scan_document(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    doc_cnt = None
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            doc_cnt = approx
            break

    if doc_cnt is None:
        return image

    pts = doc_cnt.reshape(4, 2)
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    max_width = max(int(widthA), int(widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    max_height = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (max_width, max_height))
```

---

## 19. Feature Matching and Homography Pattern

```python
import cv2
import numpy as np

def align_images(reference, target, max_matches=50):
    ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    tgt_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(ref_gray, None)
    kp2, des2 = orb.detectAndCompute(tgt_gray, None)

    matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
    matches = matcher.knnMatch(des1, des2, k=2)

    good = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good.append(m)

    good = good[:max_matches]
    if len(good) < 4:
        raise ValueError("Not enough good matches to estimate homography")

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
    aligned = cv2.warpPerspective(target, M, (reference.shape[1], reference.shape[0]))
    return aligned, M, good
```

---

## 20. OCR Preprocessing Pattern

```python
import cv2
import numpy as np

def preprocess_for_ocr(image, target_dpi=300):
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Scale to target DPI assuming original is 72 DPI
    scale = target_dpi / 72.0
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Binarize
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary
```

---

## 21. Face Detection Pattern

```python
import cv2

def detect_faces(image, scale_factor=1.1, min_neighbors=5, min_size=(30, 30)):
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=scale_factor, minNeighbors=min_neighbors, minSize=min_size
    )
    return [(int(x), int(y), int(x + w), int(y + h)) for x, y, w, h in faces]
```

For production face detection, prefer deep-learning detectors (MediaPipe, RetinaFace, YuNet, MTCNN).

---

## 22. Background Subtraction Pattern

```python
import cv2

def create_bg_subtractor(method="mog2"):
    if method == "mog2":
        return cv2.createBackgroundSubtractorMOG2()
    if method == "knn":
        return cv2.createBackgroundSubtractorKNN()
    raise ValueError(f"Unknown method: {method}")


def extract_foreground(frames, method="mog2", learning_rate=-1):
    bg = create_bg_subtractor(method)
    masks = []
    for frame in frames:
        fg = bg.apply(frame, learningRate=learning_rate)
        masks.append(fg)
    return masks
```

---

## 23. Optical Flow Pattern

```python
import cv2
import numpy as np

def compute_optical_flow(prev_frame, next_frame):
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    next_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, next_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    return flow

def flow_to_color(flow):
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    hsv = np.zeros((*flow.shape[:2], 3), dtype=np.uint8)
    hsv[..., 0] = ang * 180 / np.pi / 2
    hsv[..., 1] = 255
    hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
```

---

## 24. Non-Maximum Suppression Pattern

```python
import numpy as np

def compute_iou(box_a, box_b):
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def nms(boxes, scores, threshold=0.5):
    indices = np.argsort(scores)[::-1]
    keep = []
    while len(indices) > 0:
        current = indices[0]
        keep.append(current)
        if len(indices) == 1:
            break
        ious = np.array([compute_iou(boxes[current], boxes[i]) for i in indices[1:]])
        indices = indices[1:][ious <= threshold]
    return keep
```

---

## 25. Drawing Bounding Boxes and Labels

```python
import cv2

COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
          (255, 0, 255), (0, 255, 255)]

def draw_boxes(image, boxes, labels=None, scores=None, color=None, thickness=2):
    for i, box in enumerate(boxes):
        c = color if color else COLORS[i % len(COLORS)]
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(image, (x1, y1), (x2, y2), c, thickness)
        if labels:
            text = labels[i]
            if scores is not None:
                text += f" {scores[i]:.2f}"
            cv2.putText(image, text, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1, cv2.LINE_AA)
    return image
```

---

## 26. Mask Overlay Pattern

```python
import cv2
import numpy as np

def overlay_mask(image, mask, color=(0, 255, 0), alpha=0.5):
    colored = np.zeros_like(image)
    colored[mask > 0] = color
    return cv2.addWeighted(image, 1 - alpha, colored, alpha, 0)
```

---

## 27. Heatmap Overlay Pattern

```python
import cv2
import numpy as np

def overlay_heatmap(image, heatmap, alpha=0.5, colormap=cv2.COLORMAP_JET):
    hm = cv2.applyColorMap(np.uint8(255 * heatmap), colormap)
    return cv2.addWeighted(image, 1 - alpha, hm, alpha, 0)
```

---

## 28. Synthetic Image Generation Pattern

```python
import numpy as np
import cv2

def generate_checkerboard(size=512, n=8):
    tile = size // n
    board = np.zeros((size, size), dtype=np.uint8)
    for i in range(n):
        for j in range(n):
            if (i + j) % 2 == 0:
                board[i*tile:(i+1)*tile, j*tile:(j+1)*tile] = 255
    return cv2.cvtColor(board, cv2.COLOR_GRAY2BGR)
```

---

## 29. Image Dataset Class Pattern

```python
from torch.utils.data import Dataset
from PIL import Image, ImageOps
from pathlib import Path
import torch

class ImageLabelDataset(Dataset):
    def __init__(self, root, transform=None):
        self.root = Path(root)
        self.paths = sorted(self.root.glob("**/*.jpg")) + sorted(self.root.glob("**/*.png"))
        self.transform = transform
        self.class_to_idx = {cls.name: i for i, cls in enumerate(sorted(self.root.iterdir()))}

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        label = self.class_to_idx[path.parent.name]
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
        if self.transform:
            im = self.transform(im)
        return im, label
```

---

## 30. Inference Loop Pattern

```python
import torch

def run_inference(model, dataloader, device="cuda"):
    model.eval()
    model.to(device)
    all_outputs = []
    all_labels = []

    with torch.no_grad():
        for inputs, labels in dataloader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            all_outputs.append(outputs.cpu())
            all_labels.append(labels)

    return torch.cat(all_outputs), torch.cat(all_labels)
```

---

## 31. Model Export and ONNX Inference Pattern

```python
import torch
import cv2
import numpy as np

def export_to_onnx(model, dummy_input, path="model.onnx"):
    model.eval()
    torch.onnx.export(
        model, dummy_input, path,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        opset_version=11,
    )

def onnx_inference(session, image, input_size=(224, 224)):
    image = cv2.resize(image, input_size)
    blob = cv2.dnn.blobFromImage(image, scalefactor=1/255.0, size=input_size,
                                  mean=(0, 0, 0), swapRB=True, crop=False)
    outputs = session.run(None, {"input": blob})
    return outputs
```

---

## 32. Configuration-Driven Pipeline Pattern

Define preprocessing in a dictionary or YAML file instead of code.

```python
CONFIG = {
    "input_size": 224,
    "color_space": "rgb",
    "normalize": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
    "augmentations": [
        {"name": "RandomResizedCrop", "size": 224},
        {"name": "RandomHorizontalFlip", "p": 0.5},
        {"name": "ColorJitter", "brightness": 0.2, "contrast": 0.2},
    ],
}

def build_transform_from_config(config, is_training=True):
    from torchvision import transforms
    ops = []
    for aug in config.get("augmentations", []):
        name = aug["name"]
        if name == "RandomResizedCrop":
            ops.append(transforms.RandomResizedCrop(aug["size"]))
        elif name == "RandomHorizontalFlip":
            ops.append(transforms.RandomHorizontalFlip(aug.get("p", 0.5)))
        elif name == "ColorJitter":
            ops.append(transforms.ColorJitter(
                brightness=aug.get("brightness", 0),
                contrast=aug.get("contrast", 0),
                saturation=aug.get("saturation", 0),
                hue=aug.get("hue", 0),
            ))
    if is_training or config.get("normalize"):
        ops.append(transforms.ToTensor())
        norm = config.get("normalize")
        if norm:
            ops.append(transforms.Normalize(mean=norm["mean"], std=norm["std"]))
    return transforms.Compose(ops)
```

---

## 33. Logging and Debugging Pattern

Save intermediate pipeline stages for debugging.

```python
from pathlib import Path
import cv2

class DebugSaver:
    def __init__(self, out_dir):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.step = 0

    def save(self, image, name):
        path = self.out_dir / f"{self.step:03d}_{name}.png"
        cv2.imwrite(str(path), image)
        self.step += 1

# Usage inside pipeline
saver = DebugSaver("debug")
saver.save(img, "input")
saver.save(blurred, "blurred")
saver.save(edges, "edges")
```

---

## 34. Graceful Degradation Pattern

When a pipeline step can fail, return a default result rather than crashing the whole process.

```python
import numpy as np

def safe_resize(image, size, fallback=None):
    try:
        return cv2.resize(image, size)
    except Exception as e:
        print(f"Resize failed: {e}")
        if fallback is None:
            fallback = np.zeros((*size[::-1], 3), dtype=np.uint8)
        return fallback
```

---

## 35. Reproducible Augmentation Pattern

Always set seeds before any random operation that must be reproducible.

```python
import random
import numpy as np
import torch

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
```

---

## 36. DataLoader with Pin Memory Pattern

For GPU training, use `pin_memory=True` and `num_workers > 0`.

```python
from torch.utils.data import DataLoader

loader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=4,
    pin_memory=True,
    persistent_workers=True,
)
```

---

## 37. Validation Sanity Check Pattern

Run one batch through the model before starting full training.

```python
def sanity_check(model, loader, device="cuda"):
    model.to(device)
    batch = next(iter(loader))
    inputs = batch[0].to(device)
    outputs = model(inputs)
    assert outputs is not None
    assert not torch.isnan(outputs).any()
    print(f"Sanity check passed. Output shape: {outputs.shape}")
```

---

## 38. Handling Imbalanced Data

Use weighted sampling so rare classes appear more often in training batches.

```python
from torch.utils.data import WeightedRandomSampler
import numpy as np

class_counts = np.bincount(labels)
class_weights = 1.0 / class_counts
sample_weights = [class_weights[l] for l in labels]

sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
loader = DataLoader(dataset, batch_size=32, sampler=sampler)
```

---

## 39. Progressive Resizing Pattern

Start training with smaller images and increase resolution over time to speed up convergence.

```python
def get_transform_for_epoch(epoch, base_size=224):
    size = 160 if epoch < 5 else (192 if epoch < 10 else base_size)
    return transforms.Compose([
        transforms.Resize(size),
        transforms.RandomCrop(size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
```

---

## 40. Test-Time Augmentation Pattern

Average predictions over multiple augmented views of the same image.

```python
import torch
import torchvision.transforms as T

def tta_predict(model, image, augmentations, device="cuda"):
    model.eval()
    preds = []
    with torch.no_grad():
        for aug in augmentations:
            x = aug(image).unsqueeze(0).to(device)
            preds.append(torch.softmax(model(x), dim=1))
    return torch.stack(preds).mean(dim=0)
```

---

## 41. MixUp / CutMix Pattern

```python
import numpy as np
import torch

def mixup_data(x, y, alpha=1.0):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1
    batch_size = x.size(0)
    index = torch.randperm(batch_size)
    mixed_x = lam * x + (1 - lam) * x[index]
    return mixed_x, y, y[index], lam

def mixup_criterion(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)
```

---

## 42. Learning Rate Scheduling Pattern

```python
from torch.optim import SGD
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau

optimizer = SGD(model.parameters(), lr=0.1, momentum=0.9, weight_decay=1e-4)
scheduler = CosineAnnealingLR(optimizer, T_max=100)
# or
scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.1, patience=5)
```

---

## 43. Checkpointing Pattern

```python
import torch
from pathlib import Path

def save_checkpoint(model, optimizer, epoch, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
    }, path)

def load_checkpoint(path, model, optimizer=None):
    checkpoint = torch.load(path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint.get("epoch", 0)
```

---

## 44. Early Stopping Pattern

```python
class EarlyStopping:
    def __init__(self, patience=5, min_delta=0, restore_best=True):
        self.patience = patience
        self.min_delta = min_delta
        self.restore_best = restore_best
        self.best_score = None
        self.counter = 0
        self.best_state = None

    def __call__(self, model, score):
        if self.best_score is None or score > self.best_score + self.min_delta:
            self.best_score = score
            self.counter = 0
            if self.restore_best:
                self.best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            return False
        self.counter += 1
        if self.counter >= self.patience:
            if self.restore_best and self.best_state:
                model.load_state_dict(self.best_state)
            return True
        return False
```

---

## 45. Transfer Learning Pattern

Freeze backbone, train only the head; then optionally unfreeze and fine-tune.

```python
import torchvision

model = torchvision.models.resnet50(weights="IMAGENET1K_V2")
for param in model.parameters():
    param.requires_grad = False

num_features = model.fc.in_features
model.fc = torch.nn.Linear(num_features, num_classes)

# Phase 1: train head
# ... train ...

# Phase 2: fine-tune
for param in model.layer4.parameters():
    param.requires_grad = True
```

---

## 46. Gradient Accumulation Pattern

Simulate large batch sizes with limited GPU memory.

```python
accumulation_steps = 4
optimizer.zero_grad()

for i, (inputs, labels) in enumerate(loader):
    outputs = model(inputs)
    loss = criterion(outputs, labels) / accumulation_steps
    loss.backward()

    if (i + 1) % accumulation_steps == 0:
        optimizer.step()
        optimizer.zero_grad()
```

---

## 47. Half-Precision Training Pattern

```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

for inputs, labels in loader:
    inputs, labels = inputs.to(device), labels.to(device)
    optimizer.zero_grad()
    with autocast():
        outputs = model(inputs)
        loss = criterion(outputs, labels)
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
```

---

## 48. Distributed Training Pattern

```python
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

def setup_distributed():
    dist.init_process_group("nccl")
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)

def build_distributed_loader(dataset, batch_size):
    sampler = DistributedSampler(dataset)
    return DataLoader(dataset, batch_size=batch_size, sampler=sampler,
                      num_workers=4, pin_memory=True)

# model = DDP(model, device_ids=[local_rank])
```

---

## 49. Model Quantization Pattern

```python
import torch.quantization

model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
model_prepared = torch.quantization.prepare(model)
# run calibration batches
model_quantized = torch.quantization.convert(model_prepared)
```

---

## 50. ONNX Runtime Inference Pattern

```python
import onnxruntime as ort
import numpy as np

session = ort.InferenceSession("model.onnx", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
input_name = session.get_inputs()[0].name

output = session.run(None, {input_name: input_array})
```

---

## 51. OpenVINO Inference Pattern

```python
from openvino.runtime import Core

core = Core()
model = core.read_model("model.xml")
compiled = core.compile_model(model, "CPU")
output = compiled(input_array)
```

---

## 52. TensorRT Inference Pattern

```python
import tensorrt as trt
# Build engine from ONNX
# Serialize and deserialize
# Allocate buffers
# Execute with context
```

Use `torch_tensorrt` or `trtexec` for easier workflows.

---

## 53. Serving Pattern

For production serving, wrap inference in a FastAPI or Flask endpoint with input validation.

```python
from fastapi import FastAPI, File, UploadFile
from PIL import Image
import io
import torch

app = FastAPI()

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    image = Image.open(io.BytesIO(await file.read())).convert("RGB")
    tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        output = model(tensor)
    probs = torch.softmax(output, dim=1)[0]
    return {"class": int(probs.argmax()), "confidence": float(probs.max())}
```

---

## 54. Input Sanitization Pattern

Reject oversized or malformed inputs before decoding.

```python
from PIL import Image
import io

MAX_PIXELS = 10_000_000
MAX_FILE_SIZE = 10 * 1024 * 1024

def safe_open_image(file_bytes):
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("File too large")
    with Image.open(io.BytesIO(file_bytes)) as im:
        if im.width * im.height > MAX_PIXELS:
            raise ValueError("Image dimensions too large")
        im.load()
        return im.copy()
```

---

## 55. Caching Pattern

Cache preprocessed tensors to disk for faster epochs.

```python
from pathlib import Path
import numpy as np

def get_cached_tensor(path, cache_dir, transform):
    cache_path = Path(cache_dir) / f"{Path(path).stem}.npy"
    if cache_path.exists():
        return np.load(cache_path)
    img = load_image(path)
    tensor = transform(img).numpy()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, tensor)
    return tensor
```

---

## 56. Streaming Pattern for Large Videos

Process video frame-by-frame without loading the whole file.

```python
def process_video_stream(path, process_fn):
    cap = cv2.VideoCapture(path)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            yield process_fn(frame)
    finally:
        cap.release()
```

---

## 57. Tile-Based Processing Pattern

Process huge images in overlapping tiles.

```python
def process_tiled(image, tile_size, overlap, process_fn):
    h, w = image.shape[:2]
    output = np.zeros_like(image, dtype=np.float32)
    counts = np.zeros_like(image, dtype=np.float32)

    for y in range(0, h, tile_size - overlap):
        for x in range(0, w, tile_size - overlap):
            y2 = min(y + tile_size, h)
            x2 = min(x + tile_size, w)
            tile = image[y:y2, x:x2]
            processed = process_fn(tile)
            output[y:y2, x:x2] += processed
            counts[y:y2, x:x2] += 1

    return output / np.maximum(counts, 1e-6)
```

---

## 58. Multi-Scale Processing Pattern

Run detection or segmentation at multiple scales and merge results.

```python
scales = [0.5, 1.0, 2.0]
all_results = []
for scale in scales:
    resized = cv2.resize(image, None, fx=scale, fy=scale)
    all_results.append(detect(resized))
# merge and NMS
```

---

## 59. Model Ensemble Pattern

Average predictions from multiple models or checkpoints.

```python
def ensemble_predict(models, inputs, weights=None):
    outputs = [torch.softmax(m(inputs), dim=1) for m in models]
    if weights is None:
        weights = [1.0 / len(outputs)] * len(outputs)
    avg = sum(w * o for w, o in zip(weights, outputs))
    return avg
```

---

## 60. Summary

Good vision code is built from small, reusable, testable patterns:

- Validate inputs and normalize representations.
- Separate training and inference preprocessing.
- Keep color space, shape, and dtype conventions explicit.
- Use vectorized library calls instead of pixel loops.
- Handle errors gracefully and log intermediate results.
- Design pipelines as composable callables.
- Augment consistently across images, boxes, and masks.
- Profile and optimize hot paths (loading, resizing, augmentation).
- Version-control preprocessing configs with model checkpoints.


## 61. Pillow-Centric Patterns

### 61.1 Batch Thumbnail Generation

```python
from PIL import Image, ImageOps
from pathlib import Path

def make_thumbnails(src_dir, out_dir, size=(128, 128), fmt="JPEG"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in Path(src_dir).glob("**/*"):
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im)
                im.thumbnail(size)
                im.save(out_dir / f"{path.stem}.jpg", fmt)
        except Exception as e:
            print(f"Skipping {path}: {e}")
```

### 61.2 Watermark Pattern

```python
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

def add_watermark(image, text, opacity=0.5):
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("arial.ttf", int(image.height * 0.05))
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = image.width - text_w - 20
    y = image.height - (bbox[3] - bbox[1]) - 20
    draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255 * opacity)))
    return Image.alpha_composite(image.convert("RGBA"), overlay)
```

### 61.3 Collage Generation

```python
from PIL import Image

def create_collage(images, cols, target_size=(200, 200)):
    rows = (len(images) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * target_size[0], rows * target_size[1]))
    for i, im in enumerate(images):
        im = im.resize(target_size)
        x = (i % cols) * target_size[0]
        y = (i // cols) * target_size[1]
        canvas.paste(im, (x, y))
    return canvas
```

### 61.4 Long-Edge Resize with Pillow

```python
def resize_long_edge(im, max_size, resample=Image.Resampling.LANCZOS):
    w, h = im.size
    scale = min(max_size / max(w, h), 1.0)
    return im.resize((int(w * scale), int(h * scale)), resample)
```

---

## 62. OpenCV-Centric Patterns

### 62.1 Drawing Grid Overlay

```python
import cv2

def draw_grid(img, grid_size=50, color=(0, 255, 0), thickness=1):
    h, w = img.shape[:2]
    for x in range(0, w, grid_size):
        cv2.line(img, (x, 0), (x, h), color, thickness)
    for y in range(0, h, grid_size):
        cv2.line(img, (0, y), (w, y), color, thickness)
    return img
```

### 62.2 Splitting and Merging Channels

```python
b, g, r = cv2.split(bgr_img)
merged = cv2.merge([b, g, r])
```

### 62.3 ROI Copy Pattern

```python
roi = img[y1:y2, x1:x2].copy()
# modify roi
img[y1:y2, x1:x2] = roi
```

Always use `.copy()` if you plan to modify the ROI, otherwise the original array may be affected.

### 62.4 Mouse Callback Pattern

```python
import cv2

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Clicked at ({x}, {y})")

cv2.namedWindow("image")
cv2.setMouseCallback("image", mouse_callback)
```

### 62.5 Trackbar Pattern

```python
import cv2

def on_change(val):
    pass

cv2.namedWindow("image")
cv2.createTrackbar("threshold", "image", 127, 255, on_change)
```

---

## 63. scikit-image Patterns

### 63.1 Read and Convert

```python
from skimage import io, color, img_as_ubyte

img = io.imread("photo.jpg")            # RGB uint8
gray = color.rgb2gray(img)              # float64 [0,1]
gray_u8 = img_as_ubyte(gray)            # uint8 [0,255]
```

### 63.2 Region Properties Pattern

```python
from skimage import measure, morphology

labels = measure.label(binary_mask)
regions = measure.regionprops(labels)
for r in regions:
    print(r.label, r.area, r.bbox, r.centroid, r.eccentricity)
```

### 63.3 Skeletonization

```python
from skimage import morphology

skeleton = morphology.skeletonize(binary_mask > 0)
```

### 63.4 Active Contours

```python
from skimage.segmentation import active_contour

snake = active_contour(gray, init_points, alpha=0.015, beta=10, gamma=0.001)
```

---

## 64. Image Quality Assessment Patterns

### 64.1 Compute PSNR and SSIM

```python
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

def compare_images(ref, img):
    psnr = peak_signal_noise_ratio(ref, img, data_range=255)
    ssim = structural_similarity(ref, img, data_range=255, channel_axis=2)
    return {"psnr": psnr, "ssim": ssim}
```

### 64.2 Blur Detection

```python
import cv2

def is_blurry(image, threshold=100):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var() < threshold
```

---

## 65. Pretrained Model Usage Patterns

### 65.1 torchvision Classification

```python
import torch
from torchvision import models, transforms

model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
model.eval()

preprocess = models.ResNet50_Weights.IMAGENET1K_V2.transforms()
img_tensor = preprocess(pil_img).unsqueeze(0)

with torch.no_grad():
    logits = model(img_tensor)
    probs = torch.softmax(logits, dim=1)
```

### 65.2 torchvision Object Detection

```python
from torchvision.models.detection import fasterrcnn_resnet50_fpn

model = fasterrcnn_resnet50_fpn(weights="DEFAULT")
model.eval()

with torch.no_grad():
    predictions = model([img_tensor])
```

### 65.3 timm Pattern

```python
import timm
import torch

model = timm.create_model("efficientnet_b0", pretrained=True, num_classes=0)
model.eval()
```

---

## 66. Hugging Face Transformers Vision Pattern

```python
from transformers import AutoImageProcessor, AutoModelForImageClassification

processor = AutoImageProcessor.from_pretrained("microsoft/resnet-50")
model = AutoModelForImageClassification.from_pretrained("microsoft/resnet-50")

inputs = processor(images=pil_img, return_tensors="pt")
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
```

---

## 67. CLIP-Based Search Pattern

```python
import clip
import torch
from PIL import Image

model, preprocess = clip.load("ViT-B/32", device="cuda")

image = preprocess(pil_img).unsqueeze(0).to("cuda")
text = clip.tokenize(["a photo of a cat", "a photo of a dog"]).to("cuda")

with torch.no_grad():
    image_features = model.encode_image(image)
    text_features = model.encode_text(text)
    logits_per_image, _ = model(image, text)
    probs = logits_per_image.softmax(dim=-1)
```

---

## 68. Diffusion Inference Pattern

```python
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")
pipe = pipe.to("cuda")

image = pipe("a photo of an astronaut riding a horse on mars", num_inference_steps=50).images[0]
```

---

## 69. YOLO Inference Pattern

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model("image.jpg")

for r in results:
    boxes = r.boxes.xyxy.cpu().numpy()
    classes = r.boxes.cls.cpu().numpy()
    confidences = r.boxes.conf.cpu().numpy()
```

---

## 70. Dataset Versioning Pattern

Use DVC or a simple manifest file to version image datasets.

```python
import json
from pathlib import Path

def create_manifest(root, output="manifest.json"):
    root = Path(root)
    entries = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            entries.append({
                "path": str(path.relative_to(root)),
                "label": path.parent.name,
                "size": path.stat().st_size,
            })
    Path(output).write_text(json.dumps(entries, indent=2))
```

---

## 71. Image Deduplication Pattern

```python
from PIL import Image
import imagehash

def find_duplicates(paths):
    hashes = {}
    dups = []
    for p in paths:
        h = imagehash.average_hash(Image.open(p))
        if h in hashes:
            dups.append((p, hashes[h]))
        else:
            hashes[h] = p
    return dups
```

---

## 72. Synthetic Data Augmentation Pattern

```python
import numpy as np
import cv2

def random_shadow(image, num_shadows=1):
    h, w = image.shape[:2]
    shadow = image.copy()
    for _ in range(num_shadows):
        top_y = np.random.randint(h // 2, h)
        bot_y = np.random.randint(0, h // 2)
        top_x = np.random.randint(0, w)
        bot_x = np.random.randint(0, w)
        pts = np.array([[top_x, top_y], [bot_x, bot_y], [w, h], [0, h]], np.int32)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)
        shadow[mask > 0] = (shadow[mask > 0] * 0.6).astype(np.uint8)
    return shadow
```

---

## 73. Visualization Patterns

### 73.1 Side-by-Side Comparison

```python
import matplotlib.pyplot as plt

def show_pair(img_a, img_b, titles=("A", "B")):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, img, title in zip(axes, [img_a, img_b], titles):
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax.set_title(title)
        ax.axis("off")
    plt.tight_layout()
    plt.show()
```

### 73.2 Montage

```python
def montage(images, rows, cols, size=(100, 100)):
    canvas = np.zeros((rows * size[1], cols * size[0], 3), dtype=np.uint8)
    for i, img in enumerate(images[:rows * cols]):
        r, c = divmod(i, cols)
        img = cv2.resize(img, size)
        canvas[r*size[1]:(r+1)*size[1], c*size[0]:(c+1)*size[0]] = img
    return canvas
```

---

## 74. Metric Logging Pattern

```python
from collections import defaultdict

class Metrics:
    def __init__(self):
        self.history = defaultdict(list)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            self.history[k].append(v)

    def average(self, key):
        return sum(self.history[key]) / len(self.history[key]) if self.history[key] else 0
```

---

## 75. Hyperparameter Search Pattern

```python
import optuna

def objective(trial):
    lr = trial.suggest_float("lr", 1e-5, 1e-1, log=True)
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
    # train and return validation metric
    return val_accuracy

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=20)
```

---

## 76. Error Analysis Pattern

After training, analyze errors by class, prediction confidence, and image characteristics.

```python
def analyze_errors(model, loader, class_names):
    model.eval()
    errors = []
    with torch.no_grad():
        for inputs, labels in loader:
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            for i in range(len(labels)):
                if preds[i] != labels[i]:
                    errors.append({
                        "true": class_names[labels[i]],
                        "pred": class_names[preds[i]],
                        "conf": torch.softmax(outputs[i], dim=0)[preds[i]].item(),
                    })
    return errors
```

---

## 77. Deployment Packaging Pattern

Package model, config, and preprocessing into a single directory.

```
model_package/
  model.onnx
  config.yaml
  preprocess.py
  requirements.txt
  labels.txt
```

---

## 78. CI/CD Pattern for Vision Models

- Unit tests for preprocessing functions.
- Visual regression tests with reference images.
- Model evaluation on a held-out test set.
- Performance benchmarks (latency, throughput).
- Linting and type checking.

---

## 79. Monitoring Pattern

Log prediction distributions, confidence scores, and input statistics in production.

```python
from collections import deque

class PredictionMonitor:
    def __init__(self, window_size=1000):
        self.confidences = deque(maxlen=window_size)

    def log(self, confidence):
        self.confidences.append(confidence)

    def summary(self):
        return {
            "mean_conf": sum(self.confidences) / len(self.confidences),
            "count": len(self.confidences),
        }
```

---

## 80. Final Pattern Checklist

A well-structured vision project usually includes:

- [ ] Consistent image loading and color-space normalization.
- [ ] Separate train/val/test transforms.
- [ ] Composable preprocessing callables.
- [ ] Error handling and validation at every stage.
- [ ] Augmentation that respects task type (classification, detection, segmentation).
- [ ] Efficient data loading with appropriate `num_workers` and `pin_memory`.
- [ ] Reproducibility via seed setting.
- [ ] Checkpointing and early stopping.
- [ ] Proper model export (ONNX/TorchScript).
- [ ] Input sanitization for production.
- [ ] Logging, monitoring, and error analysis.
