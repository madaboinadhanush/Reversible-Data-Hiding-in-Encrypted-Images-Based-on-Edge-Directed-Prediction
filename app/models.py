from django.db import models

# Create your models here.


class UserModel(models.Model):
    username = models.CharField(max_length=50)
    email = models.EmailField()
    password = models.CharField(max_length=300)
    contact = models.IntegerField()
    address = models.TextField()
    profile = models.ImageField(upload_to='Profile')
    otp = models.CharField(max_length=8 , null=True)
    is_authorized = models.BooleanField(default=False)
    role = models.CharField(max_length=12 , choices=(('do','do') , ('du','du')))


    def __str__(self):
        return self.username
    
    class Meta:
        db_table = 'UserModel'



class UploadFile(models.Model):
    filename = models.CharField(max_length=255)
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    filedata = models.BinaryField()
    marked_image = models.ImageField(upload_to='MarkedImage/')
    lopt = models.IntegerField()
    key_1 = models.CharField(max_length=255)
    key_2 = models.CharField(max_length=255)
    key_3 = models.CharField(max_length=255)
    user_data_len = models.IntegerField()
    aux_bits_used = models.IntegerField(default=0)  # ADD THIS FIELD
    
    def __str__(self):
        return self.filename
    
    class Meta:
        db_table = 'UploadFile'



class RequestFile(models.Model):
    file = models.ForeignKey(UploadFile , on_delete=models.CASCADE)
    user = models.ForeignKey(UserModel , on_delete=models.CASCADE)
    status = models.CharField(max_length=20 , choices=(('accepted','accepted'), ('rejected','rejected'),('pending' , 'pending') ), default='pending')
    otp = models.CharField(max_length=8)

    def __str__(self):
        return self.file.filename , self.user.username
    
    class Meta:
        db_table = 'RequestFile'





