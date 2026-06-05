import numpy as np
import zlib

class JBIGSimulator:
    @staticmethod
    def compress(location_map: np.ndarray) -> bytes:
        """Efficient compression using packbits + zlib"""
        try:
            # Convert to binary and pack bits (8x more efficient)
            binary_map = (location_map > 0).astype(np.uint8)
            packed = np.packbits(binary_map.flatten())
            
            # Compress with zlib
            compressed = zlib.compress(packed.tobytes(), level=9)
            
            original_size = location_map.size // 8  # bits to bytes
            compressed_size = len(compressed)
            ratio = compressed_size / original_size if original_size > 0 else 0
            
            print(f"→ Compression: {original_size} bytes -> {compressed_size} bytes ({ratio:.1%})")
            return compressed
            
        except Exception as e:
            print(f"[✘] Compression failed: {e}")
            # Fallback: use raw but packed bits
            binary_map = (location_map > 0).astype(np.uint8)
            return np.packbits(binary_map.flatten()).tobytes()

    @staticmethod
    def decompress(data: bytes, shape) -> np.ndarray:
        """Decompress with proper error handling"""
        try:
            total_bits = shape[0] * shape[1]
            
            # Try to decompress
            try:
                decompressed = zlib.decompress(data)
            except zlib.error:
                # If it's not zlib compressed, use as-is
                decompressed = data
            
            # Convert to numpy array and unpack bits
            if len(decompressed) * 8 >= total_bits:
                unpacked = np.unpackbits(np.frombuffer(decompressed, dtype=np.uint8))
                location_map = unpacked[:total_bits].reshape(shape)
            else:
                # Not enough data, return zeros
                location_map = np.zeros(shape, dtype=np.uint8)
            
            ones_count = np.sum(location_map)
            print(f"→ Decompressed: {ones_count}/{total_bits} ones ({ones_count/total_bits*100:.2f}%)")
            return location_map
            
        except Exception as e:
            print(f"[✘] Decompression failed: {e}")
            return np.zeros(shape, dtype=np.uint8)