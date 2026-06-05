import numpy as np
import hashlib
import random
from app.compressor import *
from app.embedder import *

class ImageEncryptor:
    def __init__(self, key: str):
        self.key = key

    

    # --------- NOVELTY: Chaos Based Encryption ----------
    def _prng(self, shape, bitplane_index):
        h, w = shape
        
        # Generate initial value from key
        key_hash = hashlib.sha256(f"{self.key}_{bitplane_index}".encode()).hexdigest()
        x = int(key_hash[:8], 16) / 0xffffffff
        
        r = 3.99  # chaotic parameter
        
        chaos = np.zeros(h*w)
        
        for i in range(h*w):
            x = r * x * (1 - x)
            chaos[i] = 1 if x > 0.5 else 0
        
        return chaos.reshape(shape).astype(np.uint8)

    def xor_encrypt_bitplanes(self, bitplanes):
        encrypted_planes = []
        for i, plane in enumerate(bitplanes):
            rand_plane = self._prng(plane.shape, i)
            encrypted_planes.append(np.bitwise_xor(plane, rand_plane))
        return encrypted_planes

    def flatten_bitplanes_to_image(self, planes):
        img = np.zeros_like(planes[0], dtype=np.uint8)
        for k in range(8):
            img += (planes[7 - k] << k)
        return img

    

    def encrypt_image(self, bitplanes):
        encrypted_bitplanes = self.xor_encrypt_bitplanes(bitplanes)
        
        # Test decryption
        test_decrypted = self.xor_encrypt_bitplanes(encrypted_bitplanes)
        match_count = 0
        for orig, test in zip(bitplanes, test_decrypted):
            if np.array_equal(orig, test):
                match_count += 1
        
        print(f"Encryption test: {match_count}/{len(bitplanes)} planes match after round-trip")
        
        encrypted_img = self.flatten_bitplanes_to_image(encrypted_bitplanes)
        return encrypted_img, encrypted_bitplanes
    

    def decrypt_image(self, encrypted_img):
        key_len = len(self.key)
        flat = encrypted_img.flatten()
        decrypted_flat = np.array([
            px ^ self.key[i % key_len] for i, px in enumerate(flat)
        ], dtype=np.uint8)
        return decrypted_flat.reshape(encrypted_img.shape)



import cv2
from app.msb import *
from typing import Tuple
from app.embedder import *




class Downloader:
    def __init__(self, key_k1, key_k2, key_k3, encryptor_cls=ImageEncryptor, embedder_cls=Embedder):
        self.key_k1 = key_k1.decode('utf-8') if isinstance(key_k1, bytes) else str(key_k1)
        self.key_k2 = key_k2.decode('utf-8') if isinstance(key_k2, bytes) else str(key_k2)  
        self.key_k3 = key_k3.decode('utf-8') if isinstance(key_k3, bytes) else str(key_k3)
        
        print(f"Downloader keys - K1: '{self.key_k1}', K2: '{self.key_k2}', K3: '{self.key_k3}'")
        
        self.encryptor = encryptor_cls(self.key_k1)
        self.embedder = embedder_cls(self.key_k2, self.key_k3)
        self.msb_predictor = MultiMSBSelfPredictor()



   

    def download_and_decrypt(self, marked_img: np.ndarray, expected_user_data_length=20, expected_lopt=None, aux_bits_used=0):
        if marked_img is None or len(marked_img.shape) != 2:
            raise ValueError("Invalid grayscale image for decryption")

        shape = marked_img.shape
        H, W = shape

        print("\n" + "="*50)
        print("🚀 STARTING DECRYPTION PROCESS")
        print("="*50)

        print("✓ Step 1: Extract bitplanes from marked image")
        bitplanes = self.msb_predictor.extract_bit_planes(marked_img)
        print(f"→ Extracted {len(bitplanes)} bitplanes")

        print("✓ Step 2: Decrypt bitplanes using key_k1")
        decrypted_planes = self.encryptor.xor_encrypt_bitplanes(bitplanes)
        print("→ Bitplanes decrypted")

        print("✓ Step 3: Use Lopt from database")
        lopt_from_db = expected_lopt or 1
        print(f"→ Lopt: {lopt_from_db}")

        print("✓ Step 4: Extract compressed location maps")
        compressed_maps = self.embedder.extract_compressed_maps(
            decrypted_planes[:lopt_from_db], aux_bits_used, shape
        )
        print(f"→ Extracted {len(compressed_maps)} compressed maps")

        print("✓ Step 5: Decompress location maps")
        location_maps = []
        for i, comp_map in enumerate(compressed_maps):
            try:
                decompressed = JBIGSimulator.decompress(comp_map, shape)
                ones_count = np.sum(decompressed)
                location_maps.append(decompressed)
                print(f"→ Map {i}: {ones_count} ones")
                
                # DEBUG: Check if decompressed is valid
                if ones_count == 0:
                    print(f"⚠️ Map {i} is all zeros after decompression!")
                    # Check if compression might have lost data
                    print(f"   Compressed size: {len(comp_map)} bytes")
                    
            except Exception as e:
                print(f"[!] Failed to decompress map {i}: {e}")
                location_maps.append(np.zeros(shape, dtype=np.uint8))

        print("✓ Step 6: Extract user data")
        user_data = self.embedder.extract_user_data(
            decrypted_planes[lopt_from_db - 1],
            expected_user_data_length,
            shape,
            aux_bits_used
        )
        print(f"→ User data: '{user_data}'")

        print("✓ Step 7: 🔥 RESTORE ORIGINAL IMAGE")
        
        # If location maps are empty, we need to understand why
        total_ones = sum(np.sum(lm) for lm in location_maps)
        if total_ones == 0:
            print("⚠️ CRITICAL: All location maps are empty after decompression!")
            print("→ This suggests the compression/decompression lost data")
            print("→ OR the location maps were empty from the beginning")
            
            # Try a different approach: Assume no restoration needed
            print("→ Assuming marked image IS the original (no bits were flipped)")
            final_img = self.encryptor.flatten_bitplanes_to_image(decrypted_planes)
        else:
            # Use the improved restoration
            restored_planes, final_img = self.msb_predictor.restore_image(
                decrypted_planes, 
                location_maps, 
                lopt_from_db, 
                shape
            )
        
        print(f"✅ Final image: mean={final_img.mean():.2f}, range={final_img.min()}-{final_img.max()}")
        print(f"✅ User data: '{user_data}'")

        return final_img, user_data


    def restore_original_bitplanes_simple(self, marked_planes, location_maps, Lopt, shape):
        """Simple bit-flipping approach (as backup)"""
        print("🔄 Simple bitplane restoration (backup method)...")
        
        H, W = shape
        restored_planes = []
        
        # Copy all planes first
        for plane in marked_planes:
            restored_planes.append(plane.copy())
        
        # Restore each modified bitplane
        for l in range(Lopt):
            bitplane_index = 7 - l
            
            if l < len(location_maps):
                location_map = location_maps[l]
                ones_count = np.sum(location_map)
                print(f"→ Restoring bitplane {bitplane_index} using {ones_count} ones")
                
                if ones_count > 0:
                    # Simple bit flipping
                    restored_planes[bitplane_index] = np.bitwise_xor(
                        restored_planes[bitplane_index],
                        location_map
                    )
        
        return restored_planes