import datetime
from decimal import Decimal

from komtet_kassa_linux.devices.atol.receipt import Agent, Supplier
from komtet_kassa_linux.devices.atol.receipt_v1 import ReceiptV1
from komtet_kassa_linux.libs.helpers import to_decimal


def receipt_v1_factory(driver, ffd_version, task):
    '''
        Метод обхода JSON чека v1 структуры
        Результат выполнения - сформированный объект receipt.
    '''
    receipt = ReceiptV1(driver, ffd_version)
    receipt.set_intent(task['intent'])

    if True: # utilsGetChequeVATIDLessOperatorNameAvailability
        utilsOperator = ''
        utilsOperatorVATID = ''
        if task['cashier']:
            utilsOperator = task['cashier']
        receipt.set_cashier(utilsOperator, utilsOperatorVATID)
    else:
        if task['cashier']:
            receipt.set_cashier(task['cashier'], task['cashier_inn'])

    if task.get('client'):
        receipt.set_client(task['client'].get('inn'), task['client'].get('name'))

    receipt.sno = task['sno']

    if task.get('user'):
        receipt.email = task['user']

    if task.get('internet'):
        receipt.internet = task['internet']

    if task.get('additional_user_props'):
        receipt.set_additional_user_props(task['additional_user_props']['name'],
                                          task['additional_user_props']['value'])

    if task.get('additional_check_props'):
        receipt.set_additional_check_props(task['additional_check_props'])

    if 'correction' in task:
        receipt.set_correction_info(
            type=task['correction']['type'],
            date=datetime.datetime.strptime(task['correction']['date'], "%Y-%m-%d"),
            document=task['correction'].get('document')
        )
    else:
        receipt.payment_address = task.get('payment_address')

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
            vat=position['vat']['number'],
            measurement_unit=position.get('measure_name'),
            payment_method=position.get('calculation_method'),
            payment_object=position.get('calculation_subject'),
            agent=agent, supplier=supplier,
            nomenclature_code=position.get('nomenclature_code'),
            excise=position.get('excise'),
            country_code=position.get('country_code'),
            declaration_number=position.get('declaration_number'),
            user_data=position.get('user_data')
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
