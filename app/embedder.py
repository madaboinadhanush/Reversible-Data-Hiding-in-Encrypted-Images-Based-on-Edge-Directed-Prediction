import numpy as np

class Embedder:
    
    def __init__(self, K2, K3):
        try:
            self.K2 = K2.encode() if isinstance(K2, str) else K2
            self.K3 = K3.encode() if isinstance(K3, str) else K3
            if not self.K2 or not self.K3:
                raise ValueError("Encryption keys cannot be empty")
        except Exception as e:
            raise ValueError(f"Key initialization failed: {str(e)}")

    def xor_encrypt(self, data: bytes, key: bytes):
        """Fixed XOR encryption that preserves data exactly"""
        # Ensure both data and key are bytes
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        # If key is empty, return original data
        if not key:
            return data
        
        # Simple XOR that works both ways
        result = bytearray()
        key_length = len(key)
        
        for i, byte in enumerate(data):
            result.append(byte ^ key[i % key_length])
        
        return bytes(result)

    def embed_aux_data(self, bitplanes, compressed_maps, Lopt):
        print("\n=== DEBUGGING EMBED_AUX_DATA ===")
        print(f"Number of bitplanes received: {len(bitplanes)}")
        print(f"Shapes of bitplanes: {[bp.shape for bp in bitplanes] if bitplanes else 'None'}")
        print(f"Number of compressed maps: {len(compressed_maps)}")
        print(f"Lopt value: {Lopt}")

        print("\n=== DEBUGGING EMBED_AUX_DATA ===")
    
    # Store original checksum for verification
        original_checksums = []
        for i, plane in enumerate(bitplanes):
            original_checksums.append(np.sum(plane))
            print(f"Plane {i} original checksum: {original_checksums[-1]}")

        # Enhanced validation
        if not bitplanes or len(bitplanes) == 0:
            raise ValueError("[✘] No bitplanes provided")
        if Lopt <= 0 or Lopt > 8:
            raise ValueError(f"[✘] Invalid Lopt value: {Lopt}. Must be between 1-8")
        if len(bitplanes) < Lopt:
            raise ValueError(f"[✘] Only {len(bitplanes)} planes available, but Lopt={Lopt} requested")
        if not compressed_maps:
            raise ValueError("[✘] No compressed maps provided")

        H, W = bitplanes[0].shape
        total_capacity = Lopt * H * W
        print(f"Total embedding capacity: {total_capacity} bits")

        # Initialize bitstream here to avoid reference errors
        bitstream = []
        
        # Header construction with validation
        try:
            lopt_bin = format(Lopt, '03b')
            length_bits = max(8, int(np.ceil(np.log2(H * W))))
            length_bins = []
            
            for i, comp in enumerate(compressed_maps):
                if comp is None:
                    raise ValueError(f"[✘] Compressed map {i} is None")
                comp_len = len(comp)
                if comp_len >= 2**length_bits:
                    print(f"[!] Warning: Compressed map {i} length {comp_len} exceeds {length_bits}-bit representation")
                length_bins.append(format(min(comp_len, 2**length_bits-1), f'0{length_bits}b'))
            
            header_bin = lopt_bin + ''.join(length_bins)
            print(f"Header binary ({len(header_bin)} bits): {header_bin}")
            print(f"Lopt in header: {Lopt} -> {lopt_bin}")
            
            # Convert binary string to bytes for encryption
            header_bytes = bytearray()
            for i in range(0, len(header_bin), 8):
                chunk = header_bin[i:i+8]
                # Pad last chunk if needed
                if len(chunk) < 8:
                    chunk = chunk + '0' * (8 - len(chunk))
                header_bytes.append(int(chunk, 2))
            
            print(f"Header bytes before encryption: {header_bytes}")
            
            # Encrypt the header
            encrypted_header = self.xor_encrypt(bytes(header_bytes), self.K2)
            print(f"Header bytes after encryption: {encrypted_header}")
            
            # Test decryption immediately
            test_decrypted = self.xor_encrypt(encrypted_header, self.K2)
            print(f"Header bytes after test decryption: {test_decrypted}")
            
            if bytes(header_bytes) != test_decrypted:
                print("[!] WARNING: Header encryption test failed!")
                print(f"    Original: {bytes(header_bytes)}")
                print(f"    Decrypted: {test_decrypted}")
                
        except Exception as e:
            raise ValueError(f"[✘] Header construction failed: {str(e)}")

        # Bitstream generation with validation
        try:
            # Header bits
            for b in encrypted_header:
                bitstream.extend((b >> i) & 1 for i in range(7, -1, -1))
            
            # Compressed maps bits
            for i, comp in enumerate(compressed_maps):
                if not comp:
                    print(f"[!] Warning: Compressed map {i} is empty")
                    continue
                for b in comp:
                    bitstream.extend((b >> i) & 1 for i in range(7, -1, -1))
        except Exception as e:
            raise ValueError(f"[✘] Bitstream generation failed: {str(e)}")

        print(f"Total bits to embed: {len(bitstream)} (Header: {len(encrypted_header)*8}, Maps: {len(bitstream)-len(encrypted_header)*8})")

        # Capacity validation
        if len(bitstream) > total_capacity:
            required_planes = int(np.ceil(len(bitstream) / (H * W)))
            raise ValueError(
                f"[✘] Data too large: {len(bitstream)} bits > {total_capacity} capacity\n"
                f"Solution: Either increase Lopt to {required_planes} or reduce data size"
            )

        # Prepare flat planes with validation
        flat_planes = []
        try:
            for i, plane in enumerate(bitplanes[:Lopt]):
                if plane.shape != (H, W):
                    raise ValueError(f"[✘] Plane {i} shape mismatch: expected {(H, W)}, got {plane.shape}")
                flat_planes.append(plane.flatten())
                print(f"Plane {i} length: {len(flat_planes[-1])}")
        except Exception as e:
            raise ValueError(f"[✘] Plane preparation failed: {str(e)}")

        # Embedding process with bounds checking
        try:
            max_capacity = len(flat_planes) * H * W
            if len(bitstream) > max_capacity:
                raise ValueError(
                    f"[✘] Bitstream too large: {len(bitstream)} bits > {max_capacity} capacity in {len(flat_planes)} planes"
                )

            for i, bit in enumerate(bitstream):
                plane_idx = i // (H * W)
                inner_idx = i % (H * W)
                
                if plane_idx >= len(flat_planes):
                    raise IndexError(
                        f"[✘] Plane index {plane_idx} out of range at bit {i}\n"
                        f"Current bits: {i}, planes: {len(flat_planes)}, plane size: {H*W}\n"
                        f"Max expected plane index: {len(bitstream)//(H*W)}"
                    )
                if inner_idx >= len(flat_planes[plane_idx]):
                    raise IndexError(
                        f"[✘] Position {inner_idx} out of range in plane {plane_idx}\n"
                        f"Plane length: {len(flat_planes[plane_idx])}, needed index: {inner_idx}"
                    )
                
                flat_planes[plane_idx][inner_idx] = bit
        except IndexError as e:
            raise ValueError(f"[✘] Bit embedding failed: {str(e)}")

        total_aux_bits_used = len(bitstream)
        print(f"Total auxiliary bits used: {total_aux_bits_used}")
        print("=== AUX DATA EMBEDDING SUCCESSFUL ===")

        for i, (plane, original_sum) in enumerate(zip(flat_planes, original_checksums)):
            current_sum = np.sum(plane)
            if current_sum != original_sum:
                print(f"[!] WARNING: Plane {i} checksum changed: {original_sum} -> {current_sum}")
        
        return flat_planes, total_aux_bits_used

    def embed_user_data(self, flat_planes, user_data: str, aux_data_start_pos=0):
        print("\n=== DEBUGGING EMBED_USER_DATA ===")
        print(f"Number of flat planes: {len(flat_planes)}")
        print(f"Auxiliary data ends at bit position: {aux_data_start_pos}")
        
        if not flat_planes:
            raise ValueError("[✘] No bitplanes available")
        if not user_data:
            print("[!] Warning: No user data provided")
            return flat_planes
        
        # Data preparation with XOR verification
        try:
            user_bytes = user_data.encode('utf-8')
            print(f"Original user bytes: {user_bytes}")
            
            # Test XOR encryption/decryption cycle
            test_encrypted = self.xor_encrypt(user_bytes, self.K3)
            test_decrypted = self.xor_encrypt(test_encrypted, self.K3)
            
            print(f"XOR test - Original: {user_bytes}")
            print(f"XOR test - Encrypted: {test_encrypted}") 
            print(f"XOR test - Decrypted: {test_decrypted}")
            print(f"XOR test - Match: {user_bytes == test_decrypted}")
            
            if user_bytes != test_decrypted:
                print("[!] CRITICAL: XOR encryption test failed! K3 key is broken!")
                # Try with a simple key for testing
                print("Trying with simple key 'test' for debugging...")
                self.K3 = b'test'  # Fallback key
                test_encrypted = self.xor_encrypt(user_bytes, self.K3)
                test_decrypted = self.xor_encrypt(test_encrypted, self.K3)
                print(f"Fallback test - Match: {user_bytes == test_decrypted}")
            
            enc_user = self.xor_encrypt(user_bytes, self.K3)
            print(f"User data: '{user_data}' -> {len(user_bytes)} bytes -> {len(enc_user)} encrypted bytes")
        except Exception as e:
            raise ValueError(f"[✘] User data preparation failed: {str(e)}")

    # ... rest of the method remains the same ...

        last_plane = flat_planes[-1]
        capacity = len(last_plane)
        needed_bits = len(enc_user) * 8
        start_position = aux_data_start_pos
        
        print(f"Available capacity: {capacity} bits")
        print(f"Needed: {needed_bits} bits")
        print(f"Start position: {start_position}")
        print(f"End position: {start_position + needed_bits}")

        if start_position + needed_bits > capacity:
            raise ValueError(
                f"[✘] Not enough space: need {needed_bits} bits starting at {start_position}, but only {capacity} available"
            )

        # Embedding starting from the correct position
        try:
            write_plane = last_plane.copy()
            write_index = start_position
            
            for byte in enc_user:
                for bit_pos in range(7, -1, -1):
                    if write_index >= len(write_plane):
                        break
                    write_plane[write_index] = (byte >> bit_pos) & 1
                    write_index += 1
            
            flat_planes[-1] = write_plane
            print(f"Successfully embedded {write_index - start_position} bits at position {start_position}")
            print("=== USER DATA EMBEDDING SUCCESSFUL ===")
            return flat_planes
        except Exception as e:
            raise ValueError(f"[✘] User data embedding failed at index {write_index}: {str(e)}")

    def reshape_bitplanes(self, flat_planes, shape):
        print("\n=== DEBUGGING RESHAPE_BITPLANES ===")
        print(f"Input flat planes: {len(flat_planes)}")
        print(f"Target shape: {shape}")

        original_data = []
        for i, plane in enumerate(flat_planes):
            if plane is not None:
                original_data.append(plane.copy())
                print(f"Plane {i} original checksum: {np.sum(plane)}")

        # Validation
        if not flat_planes:
            raise ValueError("[✘] No planes to reshape")
        if len(shape) != 2:
            raise ValueError(f"[✘] Invalid shape {shape}. Expected (H, W)")

        h, w = shape
        expected_len = h * w
        reshaped_planes = []
        
        for i, plane in enumerate(flat_planes):
            # Debug info per plane
            print(f"\nProcessing plane {i}:")
            print(f"Original length: {len(plane) if plane is not None else 'None'}")
            print(f"Expected length: {expected_len}")

            if plane is None:
                raise ValueError(f"[✘] Plane {i} is None")
            if not isinstance(plane, np.ndarray):
                raise ValueError(f"[✘] Plane {i} is not numpy array (type: {type(plane)})")
            
            current_len = len(plane)
            
            # Length adjustment
            if current_len < expected_len:
                print(f"Padding plane {i} from {current_len} to {expected_len}")
                padded = np.zeros(expected_len, dtype=plane.dtype)
                padded[:current_len] = plane
                plane = padded
            elif current_len > expected_len:
                print(f"Truncating plane {i} from {current_len} to {expected_len}")
                plane = plane[:expected_len]
            
            # Reshaping
            try:
                reshaped = plane.reshape((h, w))
                reshaped_planes.append(reshaped)
                print(f"Successfully reshaped to {reshaped.shape}")
            except Exception as e:
                raise ValueError(
                    f"[✘] Failed to reshape plane {i} (len={len(plane)}) "
                    f"to shape {(h, w)}: {str(e)}"
                )
        for i, (original, reshaped) in enumerate(zip(original_data, reshaped_planes)):
            flat_original = original.flatten()
            flat_reshaped = reshaped.flatten()
            if len(flat_original) == len(flat_reshaped):
                match = np.array_equal(flat_original, flat_reshaped)
                print(f"Plane {i} reshape verified: {match}")
        else:
            print(f"Plane {i} length changed: {len(flat_original)} -> {len(flat_reshaped)}")
            
        print("=== RESHAPING SUCCESSFUL ===")
        return reshaped_planes

    def extract_user_data(self, bitplane, data_length, shape, aux_data_start_pos=0):
        print("\n=== DEBUG: EXTRACT_USER_DATA ===")
        print(f"Data length expected: {data_length} bytes")
        print(f"Auxiliary data ends at bit position: {aux_data_start_pos}")
        print(f"Bitplane shape: {bitplane.shape}")
        print(f"Bitplane type: {type(bitplane)}, dtype: {bitplane.dtype}")

        # Sample some bits around the extraction area to verify
        flat = bitplane.flatten()
        sample_start = max(0, aux_data_start_pos - 10)
        sample_end = min(len(flat), aux_data_start_pos + 50)
        sample_bits = flat[sample_start:sample_end]
        print(f"Sample bits around position {aux_data_start_pos}: {sample_bits}")

        total_bits_needed = data_length * 8
        start_position = aux_data_start_pos
        
        print(f"Available bits: {len(flat)}")
        print(f"Start position: {start_position}")
        print(f"Bits needed: {total_bits_needed}")

        if start_position + total_bits_needed > len(flat):
            available_bits = len(flat) - start_position
            actual_bytes = available_bits // 8
            print(f"[!] Warning: Only extracting {actual_bytes} bytes instead of {data_length}")
            total_bits_needed = actual_bytes * 8

        # Convert bits to bytes
        byte_list = []
        for i in range(start_position, start_position + total_bits_needed, 8):
            if i + 8 > len(flat):
                break
                
            byte = 0
            for j in range(8):
                byte = (byte << 1) | flat[i + j]
            byte_list.append(byte)

        enc_user_data = bytes(byte_list)
        print(f"[✓] Extracted {len(enc_user_data)} bytes of encrypted user data")
        print(f"[✓] Encrypted data (hex): {enc_user_data.hex()}")
        print(f"[✓] Encrypted data (raw): {enc_user_data}")

        # Test the XOR decryption with the same key
        print("Testing XOR decryption...")
        test_original = b'hello'
        test_encrypted = self.xor_encrypt(test_original, self.K3)
        test_decrypted = self.xor_encrypt(test_encrypted, self.K3)
        print(f"XOR test - Original: {test_original}")
        print(f"XOR test - Encrypted: {test_encrypted}")
        print(f"XOR test - Decrypted: {test_decrypted}")
        print(f"XOR test - Match: {test_original == test_decrypted}")

        # Decrypt using K3
        try:
            decrypted = self.xor_encrypt(enc_user_data, self.K3)
            print(f"[✓] Decrypted bytes: {decrypted}")
            print(f"[✓] Decrypted hex: {decrypted.hex()}")
            user_text = decrypted.decode('utf-8', errors='ignore').strip()
            print(f"[✓] Decrypted user data: '{user_text}'")
            return user_text
        except Exception as e:
            print(f"[✘] User data decryption failed: {str(e)}")
            return f"[Decryption failed: {str(e)}]"
        
    

    def extract_compressed_maps(self, bitplanes, total_aux_bits, shape):

        print("\n=== EXTRACTING COMPRESSED MAPS ===")

        H, W = shape
        flat = bitplanes[0].flatten()

        # ========== STEP 1: READ HEADER (FIRST 24 BITS) ==========
        header_bits = flat[:24]

        header_bytes = bytearray()
        for i in range(0, 24, 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | header_bits[i + j]
            header_bytes.append(byte)

        print(f"→ Encrypted header bytes: {header_bytes}")

        # ========== STEP 2: DECRYPT HEADER ==========
        decrypted_header = self.xor_encrypt(bytes(header_bytes), self.K2)

        print(f"→ Decrypted header bytes: {decrypted_header}")

        header_bin = ''.join(f'{b:08b}' for b in decrypted_header)

        print(f"→ Header binary: {header_bin}")

        # ========== STEP 3: PARSE HEADER ==========
        Lopt = int(header_bin[:3], 2)

        length_bits = int(np.ceil(np.log2(H * W)))

        comp_len = int(header_bin[3:3 + length_bits], 2)

        print(f"→ Extracted Lopt: {Lopt}")
        print(f"→ Extracted compressed length: {comp_len} bytes")

        # ========== STEP 4: EXTRACT COMPRESSED DATA ==========
        start = 24
        end = start + comp_len * 8

        comp_bits = flat[start:end]

        comp_bytes = bytearray()
        for i in range(0, len(comp_bits), 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | comp_bits[i + j]
            comp_bytes.append(byte)

        print(f"→ Extracted {len(comp_bytes)} bytes of compressed map")

        return [bytes(comp_bytes)]