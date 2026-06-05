import numpy as np 



class EdgeDirectedPredictor:
    def __init__(self, window_size=6, context_size=12):
        self.W = window_size  
        self.N = context_size 

    def get_context_indices(self):
        offsets = []
        for dy in range(-self.W, 0):
            for dx in range(-self.W, self.W + 1):
                offsets.append((dy, dx))
        return offsets

    def predict_pixel(self, img, y, x):
        context_offsets = self.get_context_indices()
        context_vectors = []
        target_values = []

        for dy, dx in context_offsets:
            yy, xx = y + dy, x + dx
            if 0 <= yy < img.shape[0] and 0 <= xx < img.shape[1]:
                neigh_values = []
                for n in range(1, self.N + 1):
                    ny, nx = yy - n // self.W, xx - (n % self.W)
                    if 0 <= ny < img.shape[0] and 0 <= nx < img.shape[1]:
                        neigh_values.append(img[ny, nx])
                    else:
                        neigh_values.append(0)
                if len(neigh_values) == self.N:
                    context_vectors.append(neigh_values)
                    target_values.append(img[yy, xx])

        if len(context_vectors) < self.N:
            return img[y, x]

        C = np.array(context_vectors)
        y_vec = np.array(target_values).reshape(-1, 1)
        try:
            a = np.linalg.inv(C.T @ C) @ (C.T @ y_vec)
        except np.linalg.LinAlgError:
            a = np.zeros((self.N, 1))

        pixel_context = []
        for n in range(1, self.N + 1):
            ny, nx = y - n // self.W, x - (n % self.W)
            if 0 <= ny < img.shape[0] and 0 <= nx < img.shape[1]:
                pixel_context.append(img[ny, nx])
            else:
                pixel_context.append(0)

        prediction = np.dot(np.array(pixel_context), a).flatten()[0]
        return np.clip(round(prediction), 0, 255)

    def predict_image(self, img):
        pred_img = np.zeros_like(img)
        for y in range(img.shape[0]):
            for x in range(img.shape[1]):
                pred_img[y, x] = self.predict_pixel(img, y, x)
        return pred_img
