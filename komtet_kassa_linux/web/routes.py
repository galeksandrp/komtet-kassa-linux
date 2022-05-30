import logging
import subprocess
import time

import requests
from flask import flash, redirect, render_template, request, url_for
from requests.exceptions import HTTPError

import komtet_kassa_linux
from komtet_kassa_linux import settings
from komtet_kassa_linux.devices.atol import DeviceManager
from komtet_kassa_linux.devices.atol.kkt import KKT
from komtet_kassa_linux.driver import Driver
from komtet_kassa_linux.libs import VIRTUAL_PRINTER_PREFIX
if True: # utilsGetWinAvailability
    import _thread
    import os
else:
    from komtet_kassa_linux.libs.htpasswd import HtpasswdFile
from komtet_kassa_linux.libs.komtet_kassa import POS
from komtet_kassa_linux.models import Printer, change_event

from . import app


logger = logging.getLogger(__name__)


@app.route('/')
def main():
    return redirect(url_for('devices'))


@app.route('/devices')
def devices():
    return render_template('printers.html', **{
        'printers': Printer.query.all(),
        'connected_devices': [serial_number for serial_number in DeviceManager().list()]
    })


@app.route('/devices/registrate', methods=['GET', 'POST'])
def registrate_printer():
    error = None
    device_manager = DeviceManager()

    if request.method == 'POST':
        pos = POS(request.form['pos_key'], request.form['pos_secret'])
        try:
            pos.activate(request.form['serial_number'], settings.LEASE_STATION)
        except HTTPError as exc:
            error = exc.response.json()['description']
            logger.warning('Activation error: %s', error)
        else:
            device = device_manager.get(request.form['serial_number'])
            printer = Printer(devname=device and device['DEVPATH'],
                              **request.form.to_dict()).save()
            logger.info('Add %s', printer)
            change_event.set()
            return redirect(url_for('devices'))

    actived_devices = Printer.query.all()
    devices = filter(lambda serial_number: serial_number not in actived_devices,
                     device_manager.list())
    return render_template('registrate_printer.html',
                           printers=devices,
                           vprinter_sn=VIRTUAL_PRINTER_PREFIX + str(int(time.time() * 10000000)),
                           error=error)


@app.route('/devices/<string:printer_number>/deactivate')
def deactivate_printer(printer_number):
    printer = Printer.query.get(printer_number)

    pos = POS(printer.pos_key, printer.pos_secret)
    try:
        pos.deactivate()
    except Exception:
        pass
    finally:
        printer.delete()
        change_event.set()
        logger.info('Remove %s', printer)

    return redirect(url_for('devices'))


@app.route('/security', methods=['GET', 'POST'])
def security():
    if request.method == 'POST':
        ht = HtpasswdFile('.htpasswd')
        ht.update('admin', request.form['password'])
        ht.save()
        return redirect(url_for('devices'))

    return render_template('security.html')


@app.route('/logout')
def logout():
    return redirect('http://out@{}'.format(request.host))


@app.route('/info')
def info():
    latest_info = requests.get(settings.LATEST_VERSION_URL).json()
    return render_template('info.html', **{
        'version': komtet_kassa_linux.__version__,
        'available_version': latest_info['version']
    })


@app.route('/upgrade')
def upgrade():
    latest_info = requests.get(settings.LATEST_VERSION_URL).json()
    logger.info('Start update to %s', latest_info['version'])
    if True: # utilsGetUpgradeReinstallAvailability
        utilsLatestInfoURL = latest_info['url']
        latest_info['url'] = '--force-reinstall --no-dependencies ' + latest_info['url']
    if True: # utilsGetWinAvailability
        try:
            _thread.interrupt_main()
        finally:
            os.execvp('cmd', [
                '/c',
                ' && '.join(['env\\Scripts\\activate',
                'pip install -U ' + latest_info['url'],
                'deactivate',
                'env\\Scripts\\kklinux'])
            ])
    else:
        subprocess.call(' && '.join([
            '. env/bin/activate',
            'pip install -U ' + latest_info['url'],
            'deactivate',
            'sudo supervisorctl restart rkm:'
        ]), shell=True)
    if True: # utilsGetUpgradeReinstallAvailability
        latest_info['url'] = utilsLatestInfoURL
    logger.info('Finish update to %s', latest_info['version'])

    if True: # utilsGetUpgradeLogoutFix
        return redirect(url_for('logout'))
    else:
        return redirect(url_for('raspberry_km.logout'))


@app.route('/devices/<string:printer_number>')
def printer_details(printer_number):
    printer = Printer.query.get(printer_number)
    device = DeviceManager().get(printer.serial_number)
    if printer and device:
        with Driver(device) as driver:
            kkt_info = KKT(driver).get_detail_info()
        return render_template(
            'printer_details.html',
            printer=printer,
            info=kkt_info,
        )
    else:
        flash('Регистратор не подключен')
        return redirect(url_for('devices'))
