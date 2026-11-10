import sys, asyncio
from PIL import Image
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog
from openthermal.image_pipeline import prepare_monochrome, raster_bytes_msb
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QTextEdit, QGroupBox, QSplitter,
    QMessageBox)

SERVICE_HINT = '0000ae30-0000-1000-8000-00805f9b34fb'
WRITE_HINT = '0000ae01-0000-1000-8000-00805f9b34fb'
NOTIFY_HINT = '0000ae02-0000-1000-8000-00805f9b34fb'

class BleWorker(QThread):
    devices = Signal(list); message = Signal(str); connected = Signal(bool)
    services = Signal(list); notification = Signal(str)
    def __init__(self):
        super().__init__(); self.loop=None; self.client=None
    def run(self):
        self.loop=asyncio.new_event_loop(); asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        pending=asyncio.all_tasks(self.loop)
        for task in pending: task.cancel()
        try: self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception: pass
        self.loop.close()
    def submit(self,coro):
        if self.loop and self.loop.is_running(): asyncio.run_coroutine_threadsafe(coro,self.loop)
    async def scan(self):
        self.message.emit('Scanning for nearby Bluetooth LE devices…')
        try:
            found=await BleakScanner.discover(timeout=8.0,return_adv=True); rows=[]
            for _,pair in found.items():
                dev,adv=pair; name=dev.name or adv.local_name or '(unnamed device)'
                uuids=adv.service_uuids or []
                hint=('SC03H' in name.upper() or 'IPRINT' in name.upper() or any('ae30' in u.lower() for u in uuids))
                rows.append({'name':name,'address':dev.address,'rssi':getattr(adv,'rssi',None),'hint':hint})
            rows.sort(key=lambda x:(not x['hint'],x['name'].lower()))
            self.devices.emit(rows); self.message.emit(f'Scan complete — {len(rows)} BLE device(s) found.')
        except Exception as e: self.message.emit(f'Scan error: {e}')
    async def connect_device(self,address):
        try:
            await self.disconnect_device(); self.message.emit(f'Connecting to {address}…')
            self.client=BleakClient(address,timeout=15.0); await self.client.connect()
            if not self.client.is_connected: raise RuntimeError('Bluetooth connection did not complete')
            self.connected.emit(True); rows=[]
            for service in self.client.services:
                rows.append(f'SERVICE  {service.uuid}  ({service.description})')
                for ch in service.characteristics:
                    rows.append(f'  CHAR  {ch.uuid}  [{", ".join(ch.properties)}]')
                    if 'notify' in ch.properties or 'indicate' in ch.properties:
                        try: await self.client.start_notify(ch.uuid,self._notify_callback); rows.append('    Notifications subscribed')
                        except Exception as e: rows.append(f'    Notify subscription failed: {e}')
            self.services.emit(rows)
            su=[s.uuid.lower() for s in self.client.services]
            cu=[c.uuid.lower() for s in self.client.services for c in s.characteristics]
            self.message.emit('Expected AE30/AE01/AE02 profile found.' if SERVICE_HINT in su and WRITE_HINT in cu and NOTIFY_HINT in cu else 'Connected; inspect the GATT UUID list. Expected profile not fully detected.')
        except Exception as e:
            self.connected.emit(False); self.message.emit(f'Connection failed: {e}'); self.client=None
    def _notify_callback(self,sender,data): self.notification.emit(f'{sender}: {bytes(data).hex(" ").upper()}')
    async def disconnect_device(self):
        if self.client:
            try:
                if self.client.is_connected: await self.client.disconnect()
            except Exception: pass
            self.client=None
        self.connected.emit(False)
    def shutdown(self):
        if self.loop and self.loop.is_running():
            self.submit(self.disconnect_device()); self.loop.call_soon_threadsafe(self.loop.stop)

from bleak import BleakScanner, BleakClient

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('OpenThermal — SC03h Windows Controller'); self.resize(1080,720)
        self.worker=BleWorker(); self.worker.devices.connect(self.show_devices); self.worker.message.connect(self.status.setText) if hasattr(self,'status') else None
        self.worker.connected.connect(self.set_connected); self.worker.services.connect(self.show_services); self.worker.notification.connect(self.log_line)
        self.worker.start(); self.build_ui()
        self.worker.message.connect(self.status.setText)
    def build_ui(self):
        root=QWidget(); outer=QVBoxLayout(root)
        title=QLabel('OpenThermal  •  SC03h / iPrint Windows Controller'); title.setStyleSheet('font-size:22px;font-weight:bold'); outer.addWidget(title)
        self.status=QLabel('Ready. Turn on SC03h-3714 and scan.'); outer.addWidget(self.status)
        split=QSplitter(Qt.Horizontal); left=QWidget(); ll=QVBoxLayout(left); self.device_list=QListWidget(); ll.addWidget(self.device_list)
        row=QHBoxLayout(); self.scan_btn=QPushButton('Scan Bluetooth'); self.scan_btn.clicked.connect(lambda:self.worker.submit(self.worker.scan()))
        self.connect_btn=QPushButton('Connect'); self.connect_btn.clicked.connect(self.connect_selected)
        self.disconnect_btn=QPushButton('Disconnect'); self.disconnect_btn.setEnabled(False); self.disconnect_btn.clicked.connect(lambda:self.worker.submit(self.worker.disconnect_device()))
        row.addWidget(self.scan_btn); row.addWidget(self.connect_btn); row.addWidget(self.disconnect_btn); ll.addLayout(row)
        right=QWidget(); rl=QVBoxLayout(right); rl.addWidget(QLabel('Printer GATT services / characteristics'))
        self.service_log=QTextEdit(); self.service_log.setReadOnly(True); rl.addWidget(self.service_log)
        studio=QGroupBox('Image preparation — 384-dot preview'); sl=QVBoxLayout(studio)
        file_row=QHBoxLayout(); self.image_path=QLabel('No image selected'); file_row.addWidget(self.image_path,1)
        browse=QPushButton('Choose image'); browse.clicked.connect(self.choose_image); file_row.addWidget(browse); sl.addLayout(file_row)
        self.preview=QLabel('Choose a PNG, JPG, BMP or WebP image'); self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(190); self.preview.setStyleSheet('background:white;color:#334155;border:1px dashed #64748b;padding:8px')
        sl.addWidget(self.preview,1)
        self.image_info=QLabel('Preview only — no printer data will be sent'); sl.addWidget(self.image_info)
        rl.addWidget(studio,2)
        rl.addWidget(QLabel('Printing remains locked until SC03h compression and BLE transfer sequence are confirmed.'))
        split.addWidget(left); split.addWidget(right); outer.addWidget(split); self.log=QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(120); outer.addWidget(self.log)
        self.setCentralWidget(root); self.setStyleSheet('QMainWindow,QWidget{background:#11151c;color:#e8edf5;font-family:Segoe UI} QPushButton{background:#2767d8;color:white;padding:9px;border:0;border-radius:6px} QListWidget,QTextEdit{background:#171e28;color:#e8edf5;border:1px solid #394352;padding:6px}')
    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose image', '', 'Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if not path: return
        try:
            with Image.open(path) as source:
                prepared = prepare_monochrome(source, width=384)
                packed = raster_bytes_msb(prepared)
            pixmap = QPixmap(path)
            self.preview.setPixmap(pixmap.scaled(self.preview.width(), 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.image_path.setText(path)
            self.image_info.setText(f'{prepared.width()} × {prepared.height()} px • {len(packed):,} raw raster bytes • preview only')
            self.log_line(f'Image prepared: {prepared.width()} × {prepared.height()} px. No BLE print data sent.')
        except Exception as exc:
            QMessageBox.warning(self, 'Image error', str(exc))
    def show_devices(self,rows):
        self.device_list.clear()
        for d in rows:
            item=QListWidgetItem(f"{'★ ' if d['hint'] else ''}{d['name']} | {d['address']} | RSSI {d['rssi']}")
            item.setData(Qt.UserRole,d['address']); self.device_list.addItem(item)
    def connect_selected(self):
        item=self.device_list.currentItem()
        if not item: QMessageBox.information(self,'Select printer','Select SC03h-3714 first.'); return
        self.worker.submit(self.worker.connect_device(item.data(Qt.UserRole)))
    def show_services(self,rows): self.service_log.setPlainText('\n'.join(rows))
    def log_line(self,msg): self.log.append(msg)
    def set_connected(self,yes): self.disconnect_btn.setEnabled(yes)
    def closeEvent(self,event): self.worker.shutdown(); self.worker.wait(2500); event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv); w=MainWindow(); w.show(); sys.exit(app.exec())
