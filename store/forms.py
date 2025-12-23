from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Product

# --------------------------
# 用户注册
# --------------------------
class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    code = forms.CharField(label="邮箱验证码")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']   

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("该邮箱已被注册。")
        return email    


# --------------------------
# 登录
# --------------------------
class LoginForm(forms.Form):
    username = forms.CharField(label='用户名', max_length=150)
    password = forms.CharField(label='密码', widget=forms.PasswordInput)


# --------------------------
# 管理员添加/编辑商品
# --------------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows':4}),
        }


# --------------------------
# 下单用表单（用户填写地址）
# --------------------------
class CheckoutForm(forms.Form):
    address = forms.CharField(label="收货地址", max_length=255)


# --------------------------
# 忘记密码
# --------------------------
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label="邮箱")

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, label="新密码")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="确认新密码")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            raise forms.ValidationError("两次输入的密码不一致")
        return cleaned
