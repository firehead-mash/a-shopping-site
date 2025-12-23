# ======================
# Django 核心
# ======================
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate

# ======================
# Django 认证与权限
# ======================
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.admin.views.decorators import staff_member_required

# ======================
# Django 其他组件
# ======================
from django.contrib import messages
from django.core.mail import send_mail

# ======================
# 项目 Models
# ======================
from .models import (
    Product,
    CartItem,
    Order,
    OrderItem,
    EmailVerification,
    ProductComment,
)

# ======================
# 项目 Forms
# ======================
from .forms import (
    RegisterForm,
    LoginForm,
    CheckoutForm,
    ProductForm,
    ForgotPasswordForm,
    ResetPasswordForm,
)

# ======================
# Python 标准库
# ======================
import uuid
from decimal import Decimal


def product_list(request):
    q = request.GET.get('q', '').strip()

    products = Product.objects.all()

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )

    return render(request, 'product_list.html', {
        'products': products,
        'q': q,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            code_input = form.cleaned_data['code']

            # 检查验证码
            try:
                record = EmailVerification.objects.get(email=email)
            except EmailVerification.DoesNotExist:
                messages.error(request, '请先发送验证码')
                return render(request, 'register.html', {'form': form})

            # 验证码过期
            if record.is_expired():
                record.delete()
                messages.error(request, '验证码已过期，请重新发送')
                return render(request, 'register.html', {'form': form})

            # 验证码错误
            if record.code != code_input:
                messages.error(request, '验证码错误')
                return render(request, 'register.html', {'form': form})

            # 验证成功 → 删除验证码
            record.delete()

            # 创建用户
            user = form.save(commit=False)
            pw = form.cleaned_data['password']
            user.set_password(pw)
            user.save()

            messages.success(request, '注册成功，请登录。')
            return redirect('login')

    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            u = form.cleaned_data['username']
            p = form.cleaned_data['password']
            user = authenticate(request, username=u, password=p)
            if user:
                login(request, user)
                return redirect('product_list')
            else:
                messages.error(request, '用户名或密码错误。')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('product_list')

@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    item, created = CartItem.objects.get_or_create(user=request.user, product=product)

    if not created:
        # 库存限制
        if item.quantity + 1 > product.stock:
            messages.error(request, "库存不足，无法继续添加。")
        else:
            item.quantity += 1
            item.save()
            messages.success(request, f'已将 {product.name} 加入购物车。')
    else:
        # 首次加入购物车，检查库存
        if product.stock < 1:
            messages.error(request, "此商品已售罄。")
        else:
            item.quantity = 1
            item.save()
            messages.success(request, f'已将 {product.name} 加入购物车。')

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    return redirect('product_detail', pk=pk)


@login_required
def remove_from_cart(request, item_id):
    it = get_object_or_404(CartItem, pk=item_id, user=request.user)
    it.delete()
    messages.success(request, '已从购物车移除。')
    return redirect('cart')

@login_required
def cart_view(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum([it.subtotal() for it in items]) if items else Decimal('0.00')
    return render(request, 'cart.html', {'items': items, 'total': total})

@login_required
def checkout_view(request):
    items = CartItem.objects.filter(user=request.user)
    if not items.exists():
        messages.error(request, '购物车为空。')
        return redirect('product_list')

    # ==== ★ 在用户刚进入结算页面（GET 阶段）先检查库存 ★ ====
    for it in items:
        if it.product.stock < it.quantity:
            messages.error(
                request,
                f"商品《{it.product.name}》库存不足，当前库存：{it.product.stock}"
            )
            return redirect('cart')

    total = sum([it.subtotal() for it in items])

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data['address']

            with transaction.atomic():
                # ★★★ 使用 select_for_update 锁定商品库存 ★★★
                product_ids = [it.product_id for it in items]
                locked_products = (
                    Product.objects.select_for_update()
                    .filter(id__in=product_ids)
                )

                locked_map = {p.id: p for p in locked_products}

                # ★★★ 并发场景下（二次检查库存）★★★
                for it in items:
                    product = locked_map[it.product_id]
                    if product.stock < it.quantity:
                        messages.error(
                            request,
                            f"商品《{product.name}》库存不足，当前库存：{product.stock}"
                        )
                        return redirect('cart')

                # ★★★ 库存足够 → 创建订单 ★★★
                order = Order.objects.create(
                    user=request.user,
                    total_amount=total,
                    address=address,
                    status='paid'
                )

                # 创建订单项 + 扣库存
                for it in items:
                    product = locked_map[it.product_id]

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=it.quantity,
                        unit_price=product.price
                    )

                    product.stock -= it.quantity
                    product.save()

                # 清空购物车
                items.delete()

            # ★ 生成随机验证串
            confirm_code = uuid.uuid4().hex
            order.confirm_code = confirm_code
            order.save()

            # ★ 生成确认 URL
            confirm_url = request.build_absolute_uri(
                reverse('confirm_shipment', args=[order.id, confirm_code])
            )

            # ★ 邮件通知
            try:
                send_mail(
                    subject='您的订单已创建，请确认发货',
                    message=f"您的订单已创建，总金额：{order.total_amount} 元。\n"
                            f"请点击以下链接确认发货：\n{confirm_url}",
                    from_email='3882373502@qq.com',
                    recipient_list=[request.user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print("邮件发送失败：", e)

            messages.success(request, '订单已创建，请前往邮箱确认发货。')
            return redirect('order_success')

    else:
        form = CheckoutForm()

    return render(request, 'checkout.html', {'form': form, 'total': total})



@login_required
def order_success(request):
    return render(request, 'order_success.html')

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order_list.html', {'orders': orders})

# ---------- admin web pages (simple) ----------
def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser, login_url='login')
def admin_product_list(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'admin/product_list.html', {'products': products})

@user_passes_test(is_superuser, login_url='login')
def admin_product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_product_list')
    else:
        form = ProductForm()
    return render(request, 'admin/product_add.html', {'form': form})

@user_passes_test(is_superuser, login_url='login')
def admin_product_edit(request, pk):
    p = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=p)
        if form.is_valid():
            form.save()
            return redirect('admin_product_list')
    else:
        form = ProductForm(instance=p)
    return render(request, 'admin/product_edit.html', {'form': form, 'product': p})

@user_passes_test(is_superuser, login_url='login')
def admin_product_delete(request, pk):
    p = get_object_or_404(Product, pk=pk)
    p.delete()
    return redirect('admin_product_list')

@login_required
def confirm_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status != 'paid':
        messages.error(request, '当前订单无法确认发货。')
        return redirect('order_list')

    # 修改状态为“已发货”
    order.status = 'shipped'
    order.save()

    messages.success(request, f'订单 {order.id} 已确认发货！')
    return redirect('order_list')

def confirm_shipment_view(request, order_id, code):
    order = get_object_or_404(Order, id=order_id)

    if order.confirm_code != code:
        return render(request, 'confirm_fail.html', {"msg": "验证码无效"})

    order.status = 'shipped'
    order.save()

    return render(request, 'confirm_success.html', {"order": order})

def send_code(request):
    email = request.GET.get('email')

    if not email:
        return JsonResponse({'status': 'error', 'msg': '请提供邮箱'})

    # 检查是否已存在验证码且未过期
    try:
        record = EmailVerification.objects.get(email=email)
        if not record.is_expired():
            return JsonResponse({'status': 'error', 'msg': '发送过于频繁，请稍后再试'})
        else:
            record.delete()
    except EmailVerification.DoesNotExist:
        pass

    # 生成 6 位数字验证码
    code = str(uuid.uuid4().int)[0:6]

    # 保存验证码
    EmailVerification.objects.create(email=email, code=code)

    # 发送邮件
    try:
        send_mail(
            subject='注册验证码',
            message=f'您的注册验证码为：{code} （1 分钟内有效）',
            from_email='3882373502@qq.com',
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': f'邮件发送失败：{e}'})

    return JsonResponse({'status': 'ok', 'msg': '验证码已发送'})



def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "该邮箱未注册。")
                return redirect('forgot_password')

            # 生成安全 token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_url = request.build_absolute_uri(
                reverse('reset_password', args=[uid, token])
            )

            # 发送邮件
            send_mail(
                subject='重置密码链接',
                message=f"请点击以下链接重置您的密码：\n{reset_url}",
                from_email='3882373502@qq.com',
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, "重置密码链接已发送至您的邮箱。")
            return redirect('login')
    else:
        form = ForgotPasswordForm()

    return render(request, 'forgot_password.html', {'form': form})


def reset_password_view(request, uid, token):
    try:
        uid = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid)
    except:
        user = None

    # token 校验
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "链接无效或已过期。")
        return redirect('login')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_pw = form.cleaned_data['new_password']
            user.set_password(new_pw)
            user.save()
            messages.success(request, "密码重置成功，请重新登录。")
            return redirect('login')
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {'form': form})


@login_required
def add_comment(request, pk):
    """
    POST endpoint: add comment to product pk.
    Expects 'content' in POST.
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        content = request.POST.get('content','').strip()
        if content:
            ProductComment.objects.create(product=product, user=request.user, content=content)
            messages.success(request, "评论已发布。")
        else:
            messages.error(request, "评论内容不能为空。")
    # 回到商品详情页
    return redirect('product_detail', pk=pk)


@user_passes_test(lambda u: u.is_superuser, login_url='login')
def delete_comment(request, comment_id):
    c = get_object_or_404(ProductComment, pk=comment_id)
    product_pk = c.product.pk
    c.delete()
    messages.success(request, "评论已删除。")
    return redirect('product_detail', pk=product_pk)

@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)

    if request.method == "POST":
        try:
            qty = int(request.POST.get("quantity", 1))
            if qty < 1:
                qty = 1
            item.quantity = qty
            item.save()
        except:
            pass

    return redirect('cart')

def update_cart_quantity(request):
    if request.method == "POST":
        cart_id = request.POST.get("cart_id")
        quantity = int(request.POST.get("quantity"))

        item = CartItem.objects.get(id=cart_id, user=request.user)

        # 库存检查
        if quantity > item.product.stock:
            return JsonResponse({
                'error': 'overstock',
                'max': item.product.stock,
                'message': f"最多只能购买 {item.product.stock} 件"
            })

        # 库存不能小于 1
        if quantity < 1:
            quantity = 1

        item.quantity = quantity
        item.save()

        subtotal = item.quantity * item.product.price
        items = CartItem.objects.filter(user=request.user)
        total = sum(i.quantity * i.product.price for i in items)

        return JsonResponse({
            'subtotal': subtotal,
            'total': total
        })

    return JsonResponse({'error': 'invalid request'})

@staff_member_required
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'admin/admin_orders.html', {'orders': orders})

@staff_member_required
def admin_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = OrderItem.objects.filter(order=order)

    total_amount = sum(item.unit_price * item.quantity for item in items)

    return render(request, 'admin/admin_order_detail.html', {
        'order': order,
        'items': items,
        'total_amount': total_amount,
    })

@staff_member_required
def admin_order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    status = request.POST.get("status")

    if status:
        order.status = status
        order.save()

    return redirect('admin/admin_order_detail', pk=pk)

@staff_member_required
def sales_report(request):
    # 每日销售额
    daily_sales = (
        Order.objects.filter(status__in=["paid", "shipped", "completed"])
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )

    # 商品销量排行
    top_products = (
        OrderItem.objects.values('product__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:10]
    )

    # 总销售额
    total_sales = Order.objects.filter(
        status__in=["paid", "shipped", "completed"]
    ).aggregate(Sum("total_amount"))['total_amount__sum'] or 0

    return render(request, 'admin/sales_report.html', {
        'daily_sales': daily_sales,
        'top_products': top_products,
        'total_sales': total_sales,
    })

@staff_member_required
def sales_report(request):
    # 每日销售额
    daily_sales = (
        Order.objects.filter(status__in=["paid", "shipped", "completed"])
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )

    # 转换成前端可直接使用的列表
    labels = [str(item['day']) for item in daily_sales]
    totals = [float(item['total']) for item in daily_sales]

    # 商品销量排行
    top_products = (
        OrderItem.objects.values('product__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:10]
    )

    # 总销售额
    total_sales = Order.objects.filter(
        status__in=["paid", "shipped", "completed"]
    ).aggregate(Sum("total_amount"))['total_amount__sum'] or 0

    return render(request, 'admin/sales_report.html', {
        'labels': labels,
        'totals': totals,
        'top_products': top_products,
        'total_sales': total_sales,
    })

import csv
from django.http import StreamingHttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.db.models.functions import TruncDate


class Echo:
    def write(self, value):
        return value


@staff_member_required
def export_sales_report_csv(request):
    qs = (
        Order.objects.filter(status__in=["paid", "shipped", "completed"])
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)

    def row_generator():
        # ★★★ 关键：写入 UTF-8 BOM，解决 Excel 中文乱码 ★★★
        yield '\ufeff'

        # 表头
        yield writer.writerow(['日期', '销售总额'])

        # 数据行（逐行流式输出，内存友好）
        for row in qs:
            yield writer.writerow([
                row['day'],
                row['total']
            ])

    response = StreamingHttpResponse(
        row_generator(),
        content_type='text/csv; charset=utf-8'
    )

    response['Content-Disposition'] = (
        'attachment; filename="sales_report.csv"'
    )

    return response


from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect

@login_required
def delete_account_view(request):
    user = request.user

    if request.method == 'POST':
        with transaction.atomic():
            # 1. 清空购物车
            CartItem.objects.filter(user=user).delete()

            # 2. 匿名化用户订单（保留订单数据）
            Order.objects.filter(user=user).update(user=None)

            # 3. 登出（清 session）
            logout(request)

            # 4. 删除用户本身
            user.delete()

        messages.success(request, '您的账号及相关数据已成功注销。')
        return redirect('login')

    # 防止 GET 误删
    messages.error(request, '非法请求。')
    return redirect('profile')

