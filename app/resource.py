compressor.py

=====
edp.py 


===
embedder.py
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
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    def embed_aux_data(self, bitplanes, compressed_maps, Lopt):
        # Debugging information
        print("\n=== DEBUGGING EMBED_AUX_DATA ===")
        print(f"Number of bitplanes received: {len(bitplanes)}")
        print(f"Shapes of bitplanes: {[bp.shape for bp in bitplanes] if bitplanes else 'None'}")
        print(f"Number of compressed maps: {len(compressed_maps)}")
        print(f"Lopt value: {Lopt}")

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

        # Header construction with validation
        try:
            lopt_bin = format(min(Lopt, 7), '03b')
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
            print(f"Header binary: {header_bin}")
            header_bytes = self.xor_encrypt(header_bin.encode(), self.K2)
        except Exception as e:
            raise ValueError(f"[✘] Header construction failed: {str(e)}")

        # Bitstream generation with validation
        bitstream = []
        try:
            # Header bits
            for b in header_bytes:
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

        print(f"Total bits to embed: {len(bitstream)} (Header: {len(header_bytes)*8}, Maps: {len(bitstream)-len(header_bytes)*8})")

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

        print("=== AUX DATA EMBEDDING SUCCESSFUL ===")
        return flat_planes

    def embed_user_data(self, flat_planes, user_data: str):
        print("\n=== DEBUGGING EMBED_USER_DATA ===")
        print(f"Number of flat planes: {len(flat_planes)}")
        if flat_planes:
            print(f"Last plane length: {len(flat_planes[-1]) if flat_planes[-1] is not None else 'None'}")

        # Validation
        if not flat_planes:
            raise ValueError("[✘] No bitplanes available")
        if not user_data:
            print("[!] Warning: No user data provided")
            return flat_planes
        
        if not isinstance(flat_planes[-1], np.ndarray):
            raise ValueError(f"[✘] Last plane is not numpy array (type: {type(flat_planes[-1])})")

        # Data preparation
        try:
            user_bytes = user_data.encode('utf-8')
            enc_user = self.xor_encrypt(user_bytes, self.K3)
            print(f"User data bytes: {len(user_bytes)}, encrypted: {len(enc_user)}")
        except Exception as e:
            raise ValueError(f"[✘] User data preparation failed: {str(e)}")

        last_plane = flat_planes[-1]
        capacity = len(last_plane)
        needed = len(enc_user) * 8
        print(f"Available capacity: {capacity}, needed: {needed}")

        if needed > capacity:
            raise ValueError(
                f"[✘] Need {needed} bits but only {capacity} available\n"
                f"Last plane size: {capacity}, data requires: {needed}\n"
                f"Possible solutions:\n"
                f"1. Reduce user data size\n"
                f"2. Use more planes for user data\n"
                f"3. Increase image size"
            )

        # Embedding
        try:
            write_plane = last_plane.copy()
            write_index = 0
            for byte in enc_user:
                for bit_pos in range(7, -1, -1):
                    if write_index >= len(write_plane):
                        break
                    write_plane[write_index] = (byte >> bit_pos) & 1
                    write_index += 1
            
            flat_planes[-1] = write_plane
            print(f"Successfully embedded {write_index} bits")
            print("=== USER DATA EMBEDDING SUCCESSFUL ===")
            return flat_planes
        except Exception as e:
            raise ValueError(f"[✘] User data embedding failed at index {write_index}: {str(e)}")

    def reshape_bitplanes(self, flat_planes, shape):
        print("\n=== DEBUGGING RESHAPE_BITPLANES ===")
        print(f"Input flat planes: {len(flat_planes)}")
        print(f"Target shape: {shape}")

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

        print("=== RESHAPING SUCCESSFUL ===")
        return reshaped_planes
===
encrypt.py
class ImageEncryptor:
    def __init__(self, key: str):
        self.key = key

    def _prng(self, shape, bitplane_index):
        seed = hashlib.sha256(f"{self.key}_{bitplane_index}".encode()).digest()
        rng = random.Random(seed)
        return np.array([[rng.randint(0, 1) for _ in range(shape[1])] for _ in range(shape[0])], dtype=np.uint8)

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
        encrypted_img = self.flatten_bitplanes_to_image(encrypted_bitplanes)
        return encrypted_img, 
====
msb.py 
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
            kl = 8 - l
            lm = np.zeros((H, W), dtype=np.uint8)

            for y in range(H):
                for x in range(W):
                    px_val = img[y, x]
                    px_bits = [(px_val >> i) & 1 for i in range(8)]
                    
                    known_low = sum(px_bits[k] << k for k in range(0, 8 - self.L))
                    expected_mid = sum((1 << (k - 1)) for k in range(8 - self.L, kl) if k - 1 >= 0)
                    known_high = sum(px_bits[k] << k for k in range(kl + 1, 8))

                    xl_0 = known_low + expected_mid + known_high
                    xl_1 = xl_0 + (1 << kl)

                    pred = pred_img[y, x]
                    lm[y, x] = 0 if abs(xl_0 - pred) <= abs(xl_1 - pred) else 1

            loc_maps.append(lm)

        return loc_maps
====
views.py 
def uploadfile(request):
    email = request.session.get('email')
    if not email:
        messages.error(request, "Please log in first.")
        return redirect('user_login')

    try:
        user = UserModel.objects.get(email=email)
    except UserModel.DoesNotExist:
        messages.error(request, "User does not exist.")
        return redirect('user_login')

    if request.method == 'POST':
        file = request.FILES.get('file')
        key_k1 = request.POST.get('key_k1')
        key_k2 = request.POST.get('key_k2')
        key_k3 = request.POST.get('key_k3')
        user_data = request.POST.get('user_data')

        if not all([file, key_k1, key_k2, key_k3, user_data]):
            messages.error(request, "All fields are required.")
            return redirect('uploadfile')

        try:
            temp_path = f'temp/{file.name}'
            temp_full_path = default_storage.save(temp_path, ContentFile(file.read()))
            image_path = default_storage.path(temp_full_path)
            img_pil = Image.open(image_path).convert('L')
            img_pil = img_pil.resize((256, 256))
            img_cv = np.array(img_pil)
        except Exception as e:
            messages.error(request, f"[✘] Image processing error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 1: Predicting image using fast blur")
            pred_img = cv2.blur(img_cv, (3, 3))
        except Exception as e:
            messages.error(request, f"[✘] Prediction error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 2: MSB Self-Prediction")
            max_L = 8  # Max 8 bitplanes for 8-bit grayscale
            msb_predictor = MultiMSBSelfPredictor(L=max_L)
            location_maps = msb_predictor.self_predict(img_cv, pred_img)
        except Exception as e:
            messages.error(request, f"[✘] MSB prediction error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 3: Compressing location maps")
            compressed_maps = [JBIGSimulator.compress(lm) for lm in location_maps]

            # Step 3.5: Dynamically calculate Lopt
            print("✓ Step 3.5: Calculating optimal Lopt")
            H, W = img_cv.shape
            M = H * W
            max_L = len(location_maps)

            length_bits = int(np.ceil(np.log2(M)))
            user_bits = len(user_data.encode('utf-8')) * 8
            compressed_bits = sum(len(cm) for cm in compressed_maps) * 8
            header_bits = 3 + length_bits * max_L
            required_bits = header_bits + compressed_bits + user_bits

            Lopt = int(np.ceil(required_bits / (H * W)))
            if Lopt > max_L:
                messages.error(request, f"[✘] Required Lopt={Lopt} exceeds available {max_L}. Reduce user data or image size.")
                return redirect('uploadfile')

            print(f"→ Computed Lopt={Lopt} based on bit budget")


        except Exception as e:
            messages.error(request, f"[✘] Compression error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 4: Encrypting bitplanes")
            bitplanes = msb_predictor.extract_bit_planes(img_cv)
            print(f"→ Extracted {len(bitplanes)} bitplanes")
            
            encryptor = ImageEncryptor(key_k1)
            encrypted_img, encrypted_planes = encryptor.encrypt_image(bitplanes)
            print(f"→ Encrypted {len(encrypted_planes)} planes")
        except Exception as e:
            messages.error(request, f"[✘] Encryption error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 5: Embedding data")
            embedder = Embedder(key_k2, key_k3)
            
            # Use Lopt=2 to match L=2 from predictor
            Lopt = 3 
            print(f"→ Using Lopt={Lopt} for embedding")
            

            print("Step A: Embed AUX")
            flat_planes = embedder.embed_aux_data(encrypted_planes[:Lopt], compressed_maps[:Lopt], Lopt)
            
            print("Step B: Embed USER")
            flat_planes = embedder.embed_user_data(flat_planes, user_data)
            
            print("Step C: Final reshaping")
            marked_planes = embedder.reshape_bitplanes(flat_planes, img_cv.shape)
            original_bitplanes = msb_predictor.extract_bit_planes(img_cv)
            for i in range(Lopt, 8):
                marked_planes.append(original_bitplanes[i])

            if len(marked_planes) != 8:
                raise ValueError(f"[✘] Need 8 bitplanes, got {len(marked_planes)}")

            marked_img = encryptor.flatten_bitplanes_to_image(marked_planes)
                        
        except Exception as e:
            messages.error(request, f"[✘] Embedding error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 6: Saving marked image")
            marked_path = f'MarkedImage/marked_{file.name}'
            os.makedirs(os.path.join('media', 'MarkedImage'), exist_ok=True)
            marked_full_path = os.path.join('media', marked_path)
            cv2.imwrite(marked_full_path, marked_img)

            _, buffer = cv2.imencode('.png', marked_img)
            file_bytes = buffer.tobytes()
        except Exception as e:
            messages.error(request, f"[✘] Saving marked image error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 7: Saving to DB")
            # file.seek(0)
            # file_bytes = file.read()
            UploadFile.objects.create(
                filename=file.name,
                user=user,
                file=file,
                filedata=file_bytes,
                marked_image=marked_path,
                lopt=2,
                key_1=key_k1,
                key_2=key_k2,
                key_3=key_k3,
            )
            # return redirect('uploadfile')
        except Exception as e:
            messages.error(request, f"[✘] Database save error: {e}")
            return redirect('uploadfile')

        messages.success(request, "Upload and embedding successful.")
        return render(request, 'uploadfile.html', {'success': True, 'output_url': '/' + marked_path})

    return render(request, 'uploadfile.html')
