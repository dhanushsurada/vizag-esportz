"""
Payments Views - Razorpay Order Creation & Webhook Verification
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
import razorpay
import json
import hmac
import hashlib

from .models import Payment
from players.models import Player
from tournaments.models import Tournament, Registration


def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


@login_required
def initiate_payment(request, slug):
    """Create Razorpay order for tournament registration."""
    tournament = get_object_or_404(Tournament, slug=slug, is_active=True)

    try:
        player = request.user.player_profile
    except Player.DoesNotExist:
        messages.error(request, 'Create your player profile first!')
        return redirect('players:create_profile')

    # Layer 2: Server-side duplicate payment check
    if Payment.objects.filter(player=player, tournament=tournament, status='SUCCESS').exists():
        messages.warning(request, '⚠️ Payment already completed for this tournament!')
        return redirect('tournaments:detail', slug=slug)

    if Registration.objects.filter(player=player, tournament=tournament, status='CONFIRMED').exists():
        messages.warning(request, '⚠️ You are already registered for this tournament!')
        return redirect('tournaments:detail', slug=slug)

    # Create Razorpay order
    client = get_razorpay_client()
    amount_paise = tournament.entry_fee * 100  # Convert to paise

    receipt = f"vizag_esportz_{player.id}_{tournament.id}"

    try:
        order_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': receipt,
            'notes': {
                'player_id': str(player.id),
                'tournament_id': str(tournament.id),
                'ign': player.ign,
            }
        }
        razorpay_order = client.order.create(data=order_data)

        # Save payment record (PENDING)
        try:
            payment = Payment.objects.create(
                player=player,
                tournament=tournament,
                razorpay_order_id=razorpay_order['id'],
                amount=amount_paise,
                receipt=receipt,
                status='PENDING'
            )
        except IntegrityError:
            # If pending payment exists, get it
            payment = Payment.objects.get(player=player, tournament=tournament)
            payment.razorpay_order_id = razorpay_order['id']
            payment.status = 'PENDING'
            payment.save()

    except Exception as e:
        messages.error(request, f'Payment initiation failed: {str(e)}')
        return redirect('tournaments:detail', slug=slug)

    context = {
        'tournament': tournament,
        'player': player,
        'payment': payment,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount': amount_paise,
        'amount_inr': tournament.entry_fee,
        'currency': 'INR',
        'user_name': request.user.get_full_name(),
        'user_email': request.user.email,
        'user_phone': request.user.phone or '',
        'upi_id': settings.UPI_ID,
    }
    return render(request, 'payments/payment_page.html', context)


@login_required
def payment_success(request):
    """Handle payment success redirect from Razorpay."""
    if request.method == 'GET':
        # Direct browser navigation (back button, bookmark) — redirect cleanly
        return redirect('players:dashboard')

    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        messages.error(request, 'Invalid payment response.')
        return redirect('players:dashboard')

    # Verify signature
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, '❌ Payment verification failed!')
        return redirect('players:dashboard')

    # Update payment record
    try:
        payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = 'SUCCESS'
        payment.save()

        # Create or confirm registration
        reg, created = Registration.objects.get_or_create(
            player=payment.player,
            tournament=payment.tournament,
            defaults={'status': 'CONFIRMED'}
        )
        if not created:
            reg.confirm()

        messages.success(request,
            f'✅ Payment successful! You are registered for {payment.tournament.title}!')
        return redirect('tournaments:detail', slug=payment.tournament.slug)

    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found.')
        return redirect('players:dashboard')


@login_required
def payment_failure(request):
    """Handle payment failure — record reason if available."""
    order_id = request.POST.get('razorpay_order_id') or request.GET.get('razorpay_order_id')
    reason = request.POST.get('error[description]') or request.GET.get('error[description]', 'Payment cancelled or failed')
    if order_id:
        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
            payment.mark_failed(reason=reason)
        except Payment.DoesNotExist:
            pass
    messages.error(request, f'❌ Payment failed: {reason}. You can try again.')
    return redirect('players:dashboard')


@csrf_exempt
def razorpay_webhook(request):
    """
    Razorpay Webhook - Server-side payment verification
    This is called by Razorpay servers, not the client.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    webhook_secret = settings.RAZORPAY_KEY_SECRET
    razorpay_signature = request.headers.get('X-Razorpay-Signature', '')

    # Verify webhook signature
    body = request.body
    expected_sig = hmac.new(
        webhook_secret.encode('utf-8'),
        body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, razorpay_signature):
        return HttpResponse(status=400)

    payload = json.loads(body)
    event = payload.get('event')

    if event == 'payment.captured':
        payment_entity = payload['payload']['payment']['entity']
        order_id = payment_entity.get('order_id')

        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
            if payment.status != 'SUCCESS':
                payment.razorpay_payment_id = payment_entity['id']
                payment.status = 'SUCCESS'
                payment.save()

                # Confirm registration
                reg, _ = Registration.objects.get_or_create(
                    player=payment.player,
                    tournament=payment.tournament,
                    defaults={'status': 'CONFIRMED'}
                )
                if reg.status != 'CONFIRMED':
                    reg.confirm()

        except Payment.DoesNotExist:
            pass

    elif event == 'payment.failed':
        entity = payload['payload']['payment']['entity']
        order_id = entity.get('order_id')
        reason = entity.get('error_description', 'Unknown failure')
        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
            payment.mark_failed(reason=reason)
        except Payment.DoesNotExist:
            pass

    return HttpResponse(status=200)


@login_required
def payment_history(request):
    """User's payment history."""
    try:
        player = request.user.player_profile
    except Player.DoesNotExist:
        return redirect('players:create_profile')

    payments = Payment.objects.filter(player=player).select_related('tournament').order_by('-created_at')
    return render(request, 'payments/history.html', {'payments': payments})


@login_required
def upi_submit(request, slug):
    """Handle UPI payment submission — stores transaction ID, marks PENDING for admin verification."""
    if request.method != 'POST':
        return redirect('tournaments:detail', slug=slug)

    tournament = get_object_or_404(Tournament, slug=slug, is_active=True)

    try:
        player = request.user.player_profile
    except Player.DoesNotExist:
        messages.error(request, 'Create your player profile first!')
        return redirect('players:create_profile')

    transaction_id = request.POST.get('transaction_id', '').strip()
    upi_app = request.POST.get('upi_app', 'Other')

    if not transaction_id:
        messages.error(request, 'Please enter your Transaction ID / UTR number.')
        return redirect('payments:initiate', slug=slug)

    if Registration.objects.filter(player=player, tournament=tournament).exists():
        messages.warning(request, '⚠️ You already have a registration for this tournament.')
        return redirect('tournaments:detail', slug=slug)

    # Handle payment screenshot upload
    payment_screenshot = request.FILES.get('payment_screenshot')

    try:
        reg = Registration.objects.create(
            player=player,
            tournament=tournament,
            status='PENDING',
            payment_method='UPI',
            payment_status='PENDING',
            transaction_id=transaction_id,
        )
        # Save screenshot if provided
        if payment_screenshot:
            reg.payment_proof = payment_screenshot
            reg.save(update_fields=['payment_proof'])

    except Exception as e:
        messages.error(request, f'Submission failed: {str(e)}')
        return redirect('payments:initiate', slug=slug)

    screenshot_note = ' Screenshot uploaded ✅' if payment_screenshot else ' No screenshot uploaded — please share it with admin.'
    messages.success(
        request,
        f'✅ Payment details submitted! Registration for {tournament.title} is pending admin verification. '
        f'Transaction ID: {transaction_id} ({upi_app}).{screenshot_note}'
    )
    return redirect('tournaments:detail', slug=slug)
