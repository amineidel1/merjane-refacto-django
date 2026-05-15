from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .dto.product import ProcessOrderResponse
from .repositories.order_repository import or_
from .services.implementations.product_service import ps


@csrf_exempt
@require_POST
def process_order(request, order_id):
    order = or_.find_by_id(order_id).get()
    for product in order.get_items():
        ps.process_product(product)

    response = ProcessOrderResponse(order.id)
    return JsonResponse({'id': response.id}, status=200)
