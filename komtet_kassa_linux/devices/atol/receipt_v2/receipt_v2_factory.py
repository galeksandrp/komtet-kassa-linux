import datetime
from decimal import Decimal

from komtet_kassa_linux.devices.atol.receipt import Agent, Supplier
from komtet_kassa_linux.devices.atol.receipt_v2 import ReceiptV2
from komtet_kassa_linux.libs.helpers import to_decimal


def receipt_v2_factory(driver, ffd_version, task):
    '''
        Метод обхода JSON чека v2 структуры
        Результат выполнения - сформированный объект receipt.
    '''
    receipt = ReceiptV2(driver, ffd_version)
    receipt.set_intent(task['intent'])

    if task['cashier']:
        receipt.set_cashier(task['cashier']['name'], task['cashier']['inn'])

    if task.get('internet'):
        receipt.internet = task['internet']

    if task.get('client'):
        receipt.set_client(task['client'].get('name'),
                           task['client'].get('inn'),
                           task['client'].get('birthdate'),
                           task['client'].get('citizenship'),
                           task['client'].get('document_code'),
                           task['client'].get('document_data'),
                           task['client'].get('address'))
        receipt.client = task['client'].get('email', task['client'].get('phone'))
    receipt.sno = task['company']['sno']

    if task.get('sectoral_check_props'):
        for sectoral_item in task['sectoral_check_props']:
            receipt.set_sectoral_check_props(sectoral_item['federal_id'],
                                             sectoral_item['date'],
                                             sectoral_item['number'],
                                             sectoral_item['value'])

    if task.get('operation_check_props'):
        receipt.set_operation_check_props(task['operation_check_props']['name'],
                                          task['operation_check_props']['value'],
                                          task['operation_check_props']['timestamp'])

    if task.get('additional_user_props'):
        receipt.set_additional_user_props(task['additional_user_props']['name'],
                                          task['additional_user_props']['value'])

    if task.get('additional_check_props'):
        receipt.set_additional_check_props(task['additional_check_props'])

    if 'correction_info' in task:
        receipt.set_correction_info(
            type=task['correction_info']['type'],
            date=datetime.datetime.strptime(task['correction_info']['base_date'], "%d.%m.%Y"),
            document=task['correction_info'].get('base_number')
        )
    else:
        receipt.payment_address = task['company']['payment_address']

    for position in task['positions']:
        agent = supplier = None
        if position.get('agent_info'):
            agent = Agent(position['agent_info']['type'])

            if position['agent_info'].get('paying_agent'):
                agent.set_paying_agent(position['agent_info']['paying_agent']['operation'],
                                       position['agent_info']['paying_agent']['phones'])

            if position['agent_info'].get('receive_payments_operator'):
                agent.set_receive_payments_operator(
                    position['agent_info']['receive_payments_operator']['phones']
                )

            if position['agent_info'].get('money_transfer_operator'):
                agent.set_money_transfer_operator(
                    position['agent_info']['money_transfer_operator']['phones'],
                    position['agent_info']['money_transfer_operator']['name'],
                    position['agent_info']['money_transfer_operator']['address'],
                    position['agent_info']['money_transfer_operator']['inn']
                )

            if position.get('supplier_info'):
                supplier = Supplier(
                    position['supplier_info']['phones'],
                    position['supplier_info']['name'],
                    position['supplier_info']['inn']
                )

        discount = position['price'] * position['quantity'] - position['total']
        position_discount = to_decimal(discount / position['quantity'])
        quantity = position['quantity']
        price = float(Decimal(position['price']) - position_discount)
        total = float(Decimal(position['total']))

        # Выявление экстра позиции
        # TODO: реализовать метод выявления экстрапозиции для количества меньше 1 (см. KKLease)
        has_extra_position = (total != price * quantity) and quantity > 1
        if has_extra_position:
            quantity -= 1

        position_info = dict(
            name=position['name'],
            vat=position['vat'],
            measurement_unit=position['measure'],
            payment_method=position['payment_method'],
            payment_object=position['payment_object'],
            agent=agent, supplier=supplier,
            user_data=position.get('user_data'),
            excise=position.get('excise'),
            country_code=position.get('country_code'),
            declaration_number=position.get('declaration_number'),
            mark_quantity=position.get('mark_quantity'),
            mark_code=position.get('mark_code'),
            sectoral_item_props=position.get('sectoral_item_props'),
            wholesale=position.get('wholesale'),
            planned_status=position.get('planned_status')
        )
        base_position_total = float(to_decimal(Decimal(price) * Decimal(quantity)))
        receipt.add_position(price=price, quantity=quantity, total=base_position_total,
                             discount=discount, **position_info)

        if has_extra_position:
            price = total - base_position_total
            receipt.add_position(price=price, quantity=1, total=price, **position_info)

    for payment in task['payments']:
        receipt.add_payment(payment['sum'], payment['type'])

    if task.get('cashless_payments'):
        for cashless_payment in task['cashless_payments']:
            receipt.add_cashless_payment(
                _sum=cashless_payment['sum'],
                method=cashless_payment['method'],
                _id=cashless_payment['id'],
                additional_info=cashless_payment.get('additional_info')
            )

    return receipt
