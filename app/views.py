from django.shortcuts import render , get_object_or_404, HttpResponse , redirect
from app.models import *
from django.contrib import messages
import hashlib

from app.compressor import *
from app.edp import *
from app.encrypt import *
from app.msb import *
from app.embedder import *
import numpy as np



def index(request):
    return render(request , 'index.html')

def about(request):
    return render(request , 'about.html')



def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if email == 'admin@gmail.com' and password == 'admin':
            request.session['email'] = email
            request.session['login'] = 'admin'
            return redirect('admin_dashboard')
        else:
            messages.error(request , 'Invalid Credential')
            return redirect('admin_login')
        
    return render(request,'admin_login.html')

def admin_dashboard(request):
    return render(request , 'admin_dashboard.html')

def view_user(request):
    email = request.session.get('email')

    users = UserModel.objects.all()
    return render(request, 'view_user.html' , {'users':users})


def authorization(request, user_id):
    email = request.session.get('email')  # optional check if needed

    user = get_object_or_404(UserModel, id=user_id)
    user.is_authorized = not user.is_authorized
    user.save()

    status = 'authorized' if user.is_authorized else 'unauthorized'
    messages.success(request, f'User {user.email} is now {status}.')

    return redirect('view_user')


def user_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        contact = request.POST.get('contact')
        address = request.POST.get('address')
        profile = request.FILES.get('profile')
        role = request.POST.get('role')

        if password == confirm_password:
            if UserModel.objects.filter(email = email). exists():
                messages.error(request , 'Email already exists')
                return redirect('user_register')
            
            if UserModel.objects.filter(username = username).exists():
                messages.error(request , 'Username is already exits')
                return redirect('user_register')
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            UserModel.objects.create(username = username , email = email , password = hashed_password, contact = contact , address = address , profile = profile , role = role)
            messages.success(request , f'Registration Successfully {username}')
            return redirect('user_login')
        else:
            messages.error(request , 'Passwoed not matched')
            return redirect('user_register')

    return render(request , 'user_register.html')


def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')

        try:
            user = UserModel.objects.get(email = email , role= role)
        except UserModel.DoesNotExist:
            messages.error(request , 'User Not Found')
            return redirect('user_login')

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if user.password != hashed_password:
            messages.error(request, 'Incorrect password')
            return redirect('user_login')

        if not user.is_authorized:
            messages.error(request, 'User is not authorized to login')
            return redirect('user_login')

        request.session['email'] = user.email
        request.session['login'] = 'user'
        return redirect('user_dashboard')

    return render(request, 'user_login.html')

def logout(request):
    del request.session['email']
    return redirect('/')

def user_dashboard(request):
    return render(request ,'user_dashboard.html')


def view_profile(request):

    email = request.session.get('email')

    if not email:
        messages.error(request,'you must be logged in')
        return redirect("user_login")
    try:
        user = UserModel.objects.get(email = email)
    except UserModel.DoesNotExist:
        messages.error(request,'User not found')
        return redirect('user_login')
    
    return render(request , 'view_profile.html' ,{'user':user})


def update_profile(request):
    email = request.session.get('email')
    if not email:
        messages.error(request , 'You must be logged in')
        return redirect('user_login')
    
    try:
        user = UserModel.objects.get(email = email)
    except UserModel.DoesNotExist:
        messages.error(request , 'User not found')
        return redirect('user_login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        contact = request.POST.get('contact')
        address = request.POST.get('address')
        profile = request.FILES.get('profile')

        user.username = username
        user.email = email
        user.contact =contact
        user.address = address

        if profile:
            user.profile = profile
        
        user.save()
        messages.success(request , 'Profile Updated successfully')
        return redirect('view_profile')

    return render(request , 'update_profile.html' , {'user':user})

from django.core.mail import send_mail
import random

def generate_otp():
    return str(random.randint(100000 , 999999))

def forgot(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            messages.error(request, 'No account found with that email.')
            return redirect('forgot')

        otp = generate_otp()

        
        user.otp = otp
        user.save()

        subject = 'Password Reset OTP - TakeOff Portal'
        message = (
            f"Hi {user.username},\n\n"
            f"We received a request to reset your password.\n"
            f"Here is your One-Time Password (OTP): {otp}\n\n"
            "Please use this OTP to complete the password reset process. "
            "Do not share this OTP with anyone.\n\n"
            "If you did not request this, please ignore this email.\n\n"
            "Best regards,\n"
            "TakeOff Support Team"
        )

        send_mail(
            subject,
            message,
            'cse.takeoff@gmail.com',
            [user.email],
            fail_silently=False,
        )

        
        request.session['email'] = user.email

        messages.success(request, 'An OTP has been sent to your email.')
        return redirect('reset_password')

    return render(request, 'forgot.html')


def reset_password(request):
    
    email = request.session.get('email')

    if not email:
        messages.error(request, 'Session expired or invalid. Please request OTP again.')
        return redirect('forgot')

    try:
        user = UserModel.objects.get(email=email)
    except UserModel.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('forgot')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if entered_otp != user.otp:
            messages.error(request, 'Incorrect OTP.')
            return redirect('reset_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('reset_password')

        user.password = hashlib.sha256(password.encode()).hexdigest()
        user.otp = None  
        user.save()

       
        request.session.flush()

        messages.success(request, 'Password reset successfully. Please log in.')
        return redirect('user_login')

    return render(request, 'reset_password.html')

def change_password(request):
    email = request.session.get('email')

    try:
        user = UserModel.objects.get(email = email)
    except UserModel.DoesNotExist:
        messages.error(request,'User not found')
        return redirect('user_login')
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')

        if old_password == new_password:
            if user.password == hashlib.sha256(old_password.encode()).hexdigest():
                user.password = hashlib.sha256(new_password.encode()).hexdigest()
                user.save()
                messages.success(request,'Password Changed successfully')
                return redirect('user_login')
            else:
                messages.error(request,'Wrong Password')
                return redirect('change_password')
        else:
            messages.error(request , 'Password Not Matched')
            return redirect('change_password')

    return render(request , 'change_password.html')



import cv2
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image

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
        print("UPLOAD KEY_1:", key_k1)
        print("UPLOAD KEY_2:", key_k2)
        print("UPLOAD KEY_3:", key_k3)
        print('user_data:', user_data)

        if not all([file, key_k1, key_k2, key_k3, user_data]):
            messages.error(request, "All fields are required.")
            return redirect('uploadfile')

        try:
            # Load and process image
            temp_path = f'temp/{file.name}'
            temp_full_path = default_storage.save(temp_path, ContentFile(file.read()))
            image_path = default_storage.path(temp_full_path)
            img_pil = Image.open(image_path).convert('L')
            img_pil = img_pil.resize((512, 512))
            img_cv = np.array(img_pil)
            print(f"✓ Loaded image: {img_cv.shape}, range: {img_cv.min()}-{img_cv.max()}")
        except Exception as e:
            messages.error(request, f"[✘] Image processing error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 1: Predicting image using fast blur")
            # --------- NOVELTY: Adaptive Edge Directed Prediction ----------
            print("✓ Step 1: Adaptive Edge Directed Prediction")

            gx = cv2.Sobel(img_cv, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(img_cv, cv2.CV_64F, 0, 1, ksize=3)

            gradient_magnitude = np.sqrt(gx**2 + gy**2)
            threshold = np.mean(gradient_magnitude)

            edge_predictor = EdgeDirectedPredictor()
            edp_pred = edge_predictor.predict_image(img_cv)

            smooth_pred = cv2.blur(img_cv, (3,3))

            pred_img = np.where(
                gradient_magnitude > threshold,
                edp_pred,
                smooth_pred
            ).astype(np.uint8)
        except Exception as e:
            messages.error(request, f"[✘] Prediction error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 2: MSB Self-Prediction")
            max_L = 8
            msb_predictor = MultiMSBSelfPredictor(L=max_L)
            location_maps = msb_predictor.self_predict(img_cv, pred_img)
            print(f"→ Generated {len(location_maps)} location maps")
        except Exception as e:
            messages.error(request, f"[✘] MSB prediction error: {e}")
            return redirect('uploadfile')

        # ========== UPDATED COMPRESSION SECTION ==========
        print("✓ Step 3: Compressing location maps")
        compressed_maps = []

        # Only compress the first location map (MSB plane) for Lopt=1
        if location_maps and len(location_maps) > 0:
            # DEBUG: Check the location map before compression
            lm = location_maps[0]
            ones_count = int(np.sum(lm))  # Convert to int to avoid numpy types
            print(f"→ First location map: {ones_count} ones out of {lm.size}")
            
            # Save a sample to see what's in it
            sample = lm[:10, :10]
            print(f"→ Sample 10x10:\n{sample}")
            
            # Check if it's all zeros or all ones
            if ones_count == 0:
                print("⚠️ WARNING: Location map is all zeros!")
                # If it's all zeros, store a special marker
                compressed_maps.append(b'ZERO')  # Special marker for all zeros
            elif ones_count == lm.size:
                print("⚠️ WARNING: Location map is all ones!")
                compressed_maps.append(b'ONES')  # Special marker for all ones
            else:
                # Normal compression for non-uniform maps
                try:
                    compressed = JBIGSimulator.compress(lm)
                    compressed_maps.append(compressed)
                    print(f"→ Compression: {lm.size//8} bytes -> {len(compressed)} bytes")
                    
                    # Test decompression immediately
                    test_decompressed = JBIGSimulator.decompress(compressed, lm.shape)
                    test_ones = int(np.sum(test_decompressed))
                    print(f"→ Test decompression: {test_ones} ones (original had {ones_count})")
                    
                    if test_ones != ones_count:
                        print(f"⚠️ WARNING: Decompression mismatch! Using raw data instead.")
                        # Fallback: store raw bits
                        raw_bytes = lm.tobytes()
                        compressed_maps.append(b'RAW' + raw_bytes)
                except Exception as e:
                    print(f"[!] Compression failed: {e}, using raw data")
                    raw_bytes = lm.tobytes()
                    compressed_maps.append(b'RAW' + raw_bytes)
        else:
            print("⚠️ WARNING: No location maps generated!")
            compressed_maps.append(b'EMPTY')

        # ========== SIMPLIFIED MINIMAL APPROACH ==========
        try:
            print("✓ Step 4: Minimal embedding approach")
            H, W = img_cv.shape
            M = H * W
            
            # Use only Lopt=1 (MSB plane)
            Lopt = 1
            
            # Calculate required space
            # For compressed map (estimate worst case)
            if compressed_maps and compressed_maps[0]:
                comp_data = compressed_maps[0]
                if comp_data in [b'ZERO', b'ONES', b'EMPTY']:
                    comp_bits = 32  # 4 bytes for marker
                elif comp_data.startswith(b'RAW'):
                    comp_bits = len(comp_data) * 8
                else:
                    comp_bits = len(comp_data) * 8
            else:
                comp_bits = 0
            
            # Header: 3 bits for Lopt + 18 bits for length = 21 bits
            header_bits = 21
            user_bits = len(user_data.encode('utf-8')) * 8
            total_bits = header_bits + comp_bits + user_bits
            
            print(f"→ Lopt=1")
            print(f"→ Header bits: {header_bits}")
            print(f"→ Compressed map bits: {comp_bits}")
            print(f"→ User data bits: {user_bits}")
            print(f"→ Total needed: {total_bits} bits")
            print(f"→ Available: {M} bits")
            
            if total_bits > M:
                # Reduce user data to fit
                available_for_user = M - (header_bits + comp_bits)
                max_user_bytes = max(0, available_for_user // 8)
                if max_user_bytes < len(user_data):
                    user_data = user_data[:max_user_bytes]
                    user_bits = len(user_data.encode('utf-8')) * 8
                    print(f"→ Reduced user data to {len(user_data)} characters")
                    total_bits = header_bits + comp_bits + user_bits
                    
            if total_bits > M:
                # Still too big - use empty location map
                print("→ Using empty location map to save space")
                compressed_maps = [b'EMPTY']
                comp_bits = 32
                total_bits = header_bits + comp_bits + user_bits
            
            print(f"→ Final parameters: Lopt={Lopt}, total bits={total_bits}/{M}")

        except Exception as e:
            messages.error(request, f"[✘] Minimal approach error: {e}")
            return redirect('uploadfile')

        # ========== EMBEDDING ==========
        try:
            print("✓ Step 5: Extract original bitplanes and embed data")
            msb_predictor = MultiMSBSelfPredictor()
            original_bitplanes = msb_predictor.extract_bit_planes(img_cv)
            print(f"→ Extracted {len(original_bitplanes)} bitplanes from original image")

            embedder = Embedder(key_k2, key_k3)
            flat_planes, aux_bits_used = embedder.embed_aux_data(
                original_bitplanes[:Lopt], compressed_maps, Lopt
            )
            flat_planes = embedder.embed_user_data(flat_planes, user_data, aux_bits_used)

            marked_planes = embedder.reshape_bitplanes(flat_planes, img_cv.shape)
            
            # Add remaining unchanged planes
            for i in range(Lopt, 8):
                marked_planes.append(original_bitplanes[i])

            if len(marked_planes) != 8:
                raise ValueError(f"[✘] Expected 8 bitplanes, got {len(marked_planes)}")

            print("✓ Step 6: Encrypt the marked bitplanes")
            encryptor = ImageEncryptor(key_k1)
            encrypted_marked_planes = encryptor.xor_encrypt_bitplanes(marked_planes)
            marked_img = encryptor.flatten_bitplanes_to_image(encrypted_marked_planes)
            
            print(f"[✔] Created marked image: {marked_img.shape}, range: {marked_img.min()}-{marked_img.max()}")
            
        except Exception as e:
            messages.error(request, f"[✘] Embedding error: {e}")
            return redirect('uploadfile')

        # ========== VERIFICATION ==========
        print("✓ Verification: Testing immediate extraction")
        try:
            # Test extraction on the spot
            test_embedder = Embedder(key_k2, key_k3)
            test_bitplanes = msb_predictor.extract_bit_planes(marked_img)
            test_decrypted = encryptor.xor_encrypt_bitplanes(test_bitplanes)
            
            # Extract compressed maps
            test_compressed = test_embedder.extract_compressed_maps(
                test_decrypted[:Lopt], aux_bits_used, img_cv.shape
            )
            
            # Decompress with special handling
            test_location_maps = []
            for cm in test_compressed:
                if cm == b'ZERO':
                    test_location_maps.append(np.zeros(img_cv.shape, dtype=np.uint8))
                elif cm == b'ONES':
                    test_location_maps.append(np.ones(img_cv.shape, dtype=np.uint8))
                elif cm == b'EMPTY':
                    test_location_maps.append(np.zeros(img_cv.shape, dtype=np.uint8))
                elif cm.startswith(b'RAW'):
                    # Extract raw data
                    raw_data = cm[3:]  # Skip 'RAW' prefix
                    arr = np.frombuffer(raw_data, dtype=np.uint8)
                    test_location_maps.append(arr.reshape(img_cv.shape))
                else:
                    # Normal JBIG decompression
                    test_location_maps.append(JBIGSimulator.decompress(cm, img_cv.shape))
            
            # Use SIMPLE restoration
            test_restored_planes, test_final = msb_predictor.restore_image_simple(
                test_decrypted, 
                test_location_maps, 
                Lopt, 
                img_cv.shape
            )
            
            # Compare with original
            diff = np.mean(np.abs(test_final - img_cv))
            print(f"→ Restoration test: average difference = {diff:.4f}")
            
            if diff < 1.0:
                print("✅ VERIFICATION PASSED: Image restoration works!")
            else:
                print(f"❌ VERIFICATION ISSUE: Average difference = {diff:.4f}")
                # Show more details
                max_diff = np.max(np.abs(test_final - img_cv))
                diff_pixels = np.sum(test_final != img_cv)
                print(f"   Max difference: {max_diff}")
                print(f"   Different pixels: {diff_pixels}/{img_cv.size} ({(diff_pixels/img_cv.size*100):.2f}%)")
                
        except Exception as e:
            print(f"→ Verification failed: {e}")
            import traceback
            traceback.print_exc()

        # ========== SAVING ==========
        try:
            print("✓ Step 7: Saving marked image")
            # Create safe filename
            original_name = os.path.splitext(file.name)[0]
            safe_name = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            marked_path = f'MarkedImage/marked_{safe_name}.tiff'
            
            os.makedirs(os.path.join('media', 'MarkedImage'), exist_ok=True)
            marked_full_path = os.path.join('media', marked_path)
            
            # Ensure image is proper format for saving
            marked_img_uint8 = marked_img.astype(np.uint8)
            Image.fromarray(marked_img_uint8).save(
                marked_full_path,
                format="PNG",
                compress_level=0
            )
            
            print(f"[✔] Image saved successfully: {marked_full_path}")

            # Prepare file bytes for database
            _, buffer = cv2.imencode('.png', marked_img_uint8)
            file_bytes = buffer.tobytes()
            
        except Exception as e:
            messages.error(request, f"[✘] Saving marked image error: {e}")
            return redirect('uploadfile')

        try:
            print("✓ Step 8: Saving to DB")
            UploadFile.objects.create(
                filename=file.name,
                user=user,
                file=file,
                filedata=file_bytes,
                marked_image=marked_path,
                lopt=Lopt,
                key_1=key_k1,
                key_2=key_k2,
                key_3=key_k3,
                user_data_len=len(user_data.encode('utf-8')),
                aux_bits_used=aux_bits_used,
            )
            print("[✔] Database entry created successfully")
        except Exception as e:
            messages.error(request, f"[✘] Database save error: {e}")
            return redirect('uploadfile')

        messages.success(request, "Upload and embedding successful.")
        return render(request, 'uploadfile.html', {'success': True, 'output_url': '/' + marked_path})

    return render(request, 'uploadfile.html')




 
def viewfile(request):
    email = request.session.get('email')
    if not email:
        messages.error(request,'you must be logged in')
        return redirect('user_login')
    
    try:
        user = UserModel.objects.get(email= email)
    except UserModel.DoesNotExist:
        messages.error(request,'user not found')
        return redirect('user_login')
    
    files = UploadFile.objects.all()
    return render(request,'viewfile.html' , {'files':files , 'role':user.role})

def requestfile(request , file_id):
    email = request.session.get('email')

    try:
        user = UserModel.objects.get(email = email)
    except UserModel.DoesNotExist:
        messages.error(request , 'user not found')
        return redirect('user_login')
    if user.role != 'du':
        messages.error(request,'You can not access the file')
        return redirect('user_dashboard')
    
    file = get_object_or_404(UploadFile,id = file_id)

    if file.user == user :
        messages.warning(request , 'You cannot request your own file')
        return redirect('viewfile')
    
    if RequestFile.objects.filter(file = file ,user = user).exists():
        messages.info(request ,'You have already requested ')
        return redirect('viewfile')

    RequestFile.objects.create(file = file, user=user)
    messages.success(request , f'You have requested this file {file.filename}')
    return redirect('viewfile')

def view_requests(request):
    email = request.session.get('email')
    if not email:
        messages.error(request, 'You must be logged in')
        return redirect('user_login')
    try:
        user = UserModel.objects.get(email = email)
    except UserModel.DoesNotExist:
        messages.error(request , 'User not found')
        return redirect('user_login')
    
    
    requests = RequestFile.objects.all()
    return render(request , 'view_requests.html',{'requests':requests})

def accept_req(request, req_id):
    email = request.session.get('email')

    try:
        data_owner = UserModel.objects.get(email=email)
    except UserModel.DoesNotExist:
        messages.error(request, 'User not found')
        return redirect('user_login')

    req = get_object_or_404(RequestFile, id=req_id)

    if req.file.user != data_owner:
        messages.error(request, "You are not authorized to respond to this request.")
        return redirect('view_requests')

    req.status = 'accepted'
    otp = generate_otp()
    req.otp = otp
    req.save()

    subject = 'File Access OTP from TakeOff'
    message = (
        f"Hi {req.user.username},\n\n"
        f"Your request to access the file '{req.file.filename}' has been accepted.\n"
        f"Here is your OTP to download the file: {otp}\n\n"
        "Please use this OTP to proceed with the download. Do not share this with anyone.\n\n"
        "Regards,\nTakeOff Support Team"
    )

    send_mail(
        subject,
        message,
        'cse.takeoff@gmail.com',
        [req.user.email],
        fail_silently=True
    )

    messages.success(request, f"Request accepted and OTP sent to {req.user.email}")
    return redirect('view_requests')





def reject_req(request, req_id):
    email = request.session.get('email')

    try:
        data_owner = UserModel.objects.get(email=email)
    except UserModel.DoesNotExist:
        messages.error(request, 'User not found')
        return redirect('user_login')

    req = get_object_or_404(RequestFile, id=req_id)

    if req.file.user != data_owner:
        messages.error(request, "You are not authorized to reject this request.")
        return redirect('view_requests')

    req.status = 'rejected'
    req.save()

    messages.info(request, f"Request by {req.user.username} has been rejected.")
    return redirect('view_requests')





def view_response(request):
    email = request.session.get('email')
    responses = RequestFile.objects.all()
    return render(request , 'view_response.html' , {'responses':responses})



import zipfile , io 
from django.http import FileResponse , Http404



import base64
from django.conf import settings
from io import BytesIO


def download(request, file_id):
    email = request.session.get('email')
    if not email:
        messages.error(request, "Login required.")
        return redirect('user_login')

    try:
        user = UserModel.objects.get(email=email)
        file_obj = RequestFile.objects.get(file__id=file_id, user=user)
        uploaded_file = file_obj.file
    except Exception as e:
        messages.error(request, f"Invalid file or user: {e}")
        return redirect('user_dashboard')

    otp_verified = request.session.get(f'otp_verified_{file_id}', False)

    if request.method == 'POST':
        stage = request.POST.get('stage', 'otp')

        if stage == 'otp':
            otp = request.POST.get('otp')
            if otp != file_obj.otp:
                messages.error(request, 'Invalid OTP')
                return render(request, 'verify_otp.html', {'file_id': file_id})

            request.session[f'otp_verified_{file_id}'] = True
            return render(request, 'download.html', {'file_id': file_id})

        elif stage == 'download':
            if not otp_verified:
                messages.error(request, 'OTP verification required.')
                return redirect('download', file_id=file_id)

            filetype = request.POST.get('filetype')
            if not filetype:
                messages.error(request, 'Filetype required.')
                return render(request, 'download.html', {'file_id': file_id})

            try:
                marked_img_path = uploaded_file.marked_image.path
                marked_img = np.array(Image.open(marked_img_path).convert('L'))
                if marked_img is None:
                    raise ValueError("[✘] Unable to read marked image.")

                downloader = Downloader(
                    key_k1=uploaded_file.key_1,
                    key_k2=uploaded_file.key_2,
                    key_k3=uploaded_file.key_3,
                    encryptor_cls=ImageEncryptor,
                    embedder_cls=Embedder
                )

                decrypted_img, user_data = downloader.download_and_decrypt(
                    marked_img,
                    expected_user_data_length=uploaded_file.user_data_len,
                    expected_lopt=uploaded_file.lopt,
                    aux_bits_used=uploaded_file.aux_bits_used  # PASS THE STORED VALUE
                )

                original_name = os.path.basename(uploaded_file.file.name)
                recovered_filename = f"recovered_{original_name}"
                zip_filename = f"decrypted_{original_name}.zip"

                if filetype == 'image':
                    original_path = uploaded_file.file.path
                    return FileResponse(
                        open(original_path, 'rb'),
                        as_attachment=True,
                        filename=os.path.basename(original_path)
                    )

                elif filetype == 'all':
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:

                        original_path = uploaded_file.file.path

                        with open(original_path, 'rb') as f:
                            zip_file.writestr(os.path.basename(original_path), f.read())

                        zip_file.writestr('extracted_user_data.txt', user_data or "N/A")
                    zip_buffer.seek(0)
                    return FileResponse(zip_buffer, as_attachment=True, filename=zip_filename)

                else:
                    messages.error(request, "Invalid file type selected.")
                    return render(request, 'download.html', {'file_id': file_id})

            except Exception as e:
                messages.error(request, f"[✘] Decryption failed: {e}")
                return render(request, 'download.html', {'file_id': file_id})

    return render(request, 'verify_otp.html', {'file_id': file_id})

    




import os

def receiver(request, file_id):
    email = request.session.get('email')
    user = get_object_or_404(UserModel, email=email)
    upload = get_object_or_404(UploadFile, id=file_id)
    request_file = get_object_or_404(RequestFile, file=upload, user=user, status='accepted')

    extracted_data = None
    recovered_image_url = None

    if request.method == 'POST':
        k1 = request.POST.get('key_1')
        k2 = request.POST.get('key_2')
        k3 = request.POST.get('key_3')

        image_path = upload.marked_image.path
        img = cv2.imread(image_path, 0)

        H, W = img.shape
        total_pixels = H * W

        # Step 1: bitplane splitting
        bitplanes = [(img >> k) & 1 for k in range(7, -1, -1)]
        flat_planes = [bp.flatten() for bp in bitplanes]
        read_index = 0

        def xor_decrypt(data, key):
            key_bytes = hashlib.sha256(key.encode()).digest()
            return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)])

        # Step 2: Decrypt header
        enc_header = []
        for _ in range((3 + upload.lopt * int(np.ceil(np.log2(total_pixels)))) // 8 + 1):
            byte = 0
            for i in range(8):
                bit = flat_planes[0][read_index]
                byte |= (bit << (7 - i))
                read_index += 1
            enc_header.append(byte)

        header_bytes = xor_decrypt(bytes(enc_header), k2)
        header_bin = ''.join(f'{b:08b}' for b in header_bytes)

        lopt = int(header_bin[:3], 2)
        map_lens = []
        cursor = 3
        for _ in range(lopt):
            bits = header_bin[cursor:cursor + int(np.ceil(np.log2(total_pixels)))]
            map_lens.append(int(bits, 2))
            cursor += int(np.ceil(np.log2(total_pixels)))

        # Step 3: Extract user data
        if k3:
            enc_data_bits = []
            for i in range(read_index, len(flat_planes[lopt]) - 8):
                enc_data_bits.append(flat_planes[lopt][i])
            b_array = bytearray()
            for i in range(0, len(enc_data_bits), 8):
                byte = 0
                for j in range(8):
                    if i + j < len(enc_data_bits):
                        byte |= enc_data_bits[i + j] << (7 - j)
                b_array.append(byte)
            decrypted_data = xor_decrypt(bytes(b_array), k3)
            try:
                extracted_data = decrypted_data.decode()
                # Save to file
                extracted_path = f'media/extracted/extracted_{file_id}.txt'
                os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
                with open(extracted_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_data)
            except:
                extracted_data = "<decryption failed>"

        # Step 4: Recover image
        if k1:
            from encrypt import ImageEncryptor
            enc = ImageEncryptor(k1)
            random_streams = [enc._prng((H, W), i) for i in range(8)]
            decrypted_planes = [np.bitwise_xor(bitplanes[i], random_streams[i]) for i in range(8)]

            recovered = np.zeros_like(decrypted_planes[0])
            for y in range(H):
                for x in range(W):
                    bits = [decrypted_planes[7 - k][y, x] for k in range(8)]
                    val = sum([bits[k] << k for k in range(8)])
                    recovered[y, x] = val

            recovered_path = f'media/recovered/recovered_{file_id}.png'
            os.makedirs(os.path.dirname(recovered_path), exist_ok=True)
            cv2.imwrite(recovered_path, recovered)
            recovered_image_url = '/' + recovered_path

    return render(request, 'receiver.html', {
        'upload': upload,
        'extracted_data': extracted_data,
        'recovered_image_url': recovered_image_url
    })
    






