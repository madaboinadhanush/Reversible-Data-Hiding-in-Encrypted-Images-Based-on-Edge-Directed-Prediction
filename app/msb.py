import numpy as np

class MultiMSBSelfPredictor:
    def __init__(self, L=5):
        self.L = L

    def extract_bit_planes(self, image):
        return [(image >> k) & 1 for k in range(7, -1, -1)]

    def reconstructor_bit_from_planes(self, planes):
        img = np.zeros_like(planes[0], dtype=np.uint8)
        for k in range(8):
            img += (planes[7 - k] << k)
        return img

    def self_predict(self, img, pred_img):
        H, W = img.shape
        loc_maps = []

        for l in range(1, self.L + 1):
            kl = 8 - l  # bitplane index (7, 6, 5, ...)
            lm = np.zeros((H, W), dtype=np.uint8)

            for y in range(H):
                for x in range(W):
                    px_val = img[y, x]
                    pred_val = pred_img[y, x]
                    
                    # Extract bit values
                    px_bits = [(px_val >> i) & 1 for i in range(8)]
                    
                    # Calculate the two possible values for this bitplane
                    val_if_0 = self.calculate_pixel_value(px_bits, kl, 0)
                    val_if_1 = self.calculate_pixel_value(px_bits, kl, 1)
                    
                    # FIX: Use integer arithmetic to avoid overflow
                    diff_0 = abs(int(val_if_0) - int(pred_val))
                    diff_1 = abs(int(val_if_1) - int(pred_val))
                    
                    # Determine which value is closer to prediction
                    actual_bit = px_bits[kl]
                    if actual_bit == 0:
                        lm[y, x] = 1 if diff_1 < diff_0 else 0
                    else:
                        lm[y, x] = 1 if diff_0 < diff_1 else 0

            flip_count = np.sum(lm)
            print(f"→ Location map {l} (bitplane {kl}): {flip_count}/{H*W} bits to flip ({flip_count/(H*W)*100:.2f}%)")
            loc_maps.append(lm)

        return loc_maps

    def calculate_pixel_value(self, bits, target_bitplane, assumed_bit):
        """Calculate pixel value assuming a specific bit in target_bitplane"""
        value = 0
        for i in range(8):
            if i == target_bitplane:
                bit_val = assumed_bit
            else:
                bit_val = bits[i]
            value += bit_val * (2 ** i)
        return value

    # ========== SIMPLIFIED RESTORATION METHOD ==========
    def restore_image_simple(self, marked_bitplanes, location_maps, Lopt, shape):
        """
        SIMPLE restoration: Just apply the location maps directly
        Location map == 1 means flip that bit
        """
        H, W = shape
        
        print(f"\n🔧 SIMPLE IMAGE RESTORATION: Lopt={Lopt}")
        
        # Start with the marked bitplanes
        restored_planes = [plane.copy() for plane in marked_bitplanes]
        
        # Apply each location map to its corresponding bitplane
        for l in range(min(Lopt, len(location_maps))):
            bitplane_idx = 7 - l  # MSB=7, next=6, etc.
            location_map = location_maps[l]
            
            # Count ones in location map
            ones_count = np.sum(location_map)
            print(f"→ Applying location map {l} to bitplane {bitplane_idx}: {ones_count} ones")
            
            if ones_count > 0:
                # Apply the location map: XOR with the location map
                # If location_map[y,x] == 1, flip the bit
                restored_planes[bitplane_idx] = np.bitwise_xor(
                    restored_planes[bitplane_idx],
                    location_map
                )
        
        # Reconstruct the image from bitplanes
        restored_img = self.reconstructor_bit_from_planes(restored_planes)
        
        print(f"✅ Simple restoration complete: mean={restored_img.mean():.2f}")
        return restored_planes, restored_img
    
    # ========== PREDICTION-BASED RESTORATION (Improved) ==========
    def restore_image(self, marked_bitplanes, location_maps, Lopt, shape):
        """
        Improved restoration with better handling
        """
        H, W = shape
        
        print(f"\n🔧 IMPROVED IMAGE RESTORATION: Lopt={Lopt}")
        
        # First, try the simple restoration
        restored_planes, restored_img = self.restore_image_simple(
            marked_bitplanes, location_maps, Lopt, shape
        )
        
        # If location maps are empty, we need a different approach
        total_ones = sum(np.sum(lm) for lm in location_maps)
        if total_ones == 0:
            print("⚠️ WARNING: All location maps are empty!")
            print("→ Using original marked bitplanes (no restoration needed)")
            
            # If location maps are empty, it means no bits were flipped
            # So the marked bitplanes ARE the original bitplanes
            restored_img = self.reconstructor_bit_from_planes(marked_bitplanes)
            return marked_bitplanes, restored_img
        
        return restored_planes, restored_img