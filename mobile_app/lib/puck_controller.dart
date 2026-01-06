import 'package:flutter/foundation.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'dart:async';

class PuckInfo {
  final int id;
  final String name;
  final BluetoothDevice? device;
  final int rssi;
  final int batteryLevel;
  final bool isOnline;
  final DateTime lastSeen;

  PuckInfo({
    required this.id,
    required this.name,
    this.device,
    this.rssi = -100,
    this.batteryLevel = 0,
    this.isOnline = false,
    DateTime? lastSeen,
  }) : lastSeen = lastSeen ?? DateTime.now();

  PuckInfo copyWith({
    int? id,
    String? name,
    BluetoothDevice? device,
    int? rssi,
    int? batteryLevel,
    bool? isOnline,
    DateTime? lastSeen,
  }) {
    return PuckInfo(
      id: id ?? this.id,
      name: name ?? this.name,
      device: device ?? this.device,
      rssi: rssi ?? this.rssi,
      batteryLevel: batteryLevel ?? this.batteryLevel,
      isOnline: isOnline ?? this.isOnline,
      lastSeen: lastSeen ?? this.lastSeen,
    );
  }
}

class PuckController extends ChangeNotifier {
  final List<PuckInfo> _pucks = [];
  bool _isScanning = false;
  String _serverUrl = 'http://192.168.1.100:5000'; // Configure this
  StreamSubscription? _scanSubscription;

  List<PuckInfo> get pucks => _pucks;
  bool get isScanning => _isScanning;
  String get serverUrl => _serverUrl;

  int get activePuckCount => _pucks.where((p) => p.isOnline).length;

  // ============================================================================
  // BLE SCANNING
  // ============================================================================

  Future<void> startScan() async {
    if (_isScanning) return;

    _isScanning = true;
    _pucks.clear();
    notifyListeners();

    try {
      // Check if Bluetooth is available
      if (await FlutterBluePlus.isSupported == false) {
        debugPrint("Bluetooth not supported by this device");
        _isScanning = false;
        notifyListeners();
        return;
      }

      // Start scanning
      await FlutterBluePlus.startScan(timeout: const Duration(seconds: 10));

      // Listen for scan results
      _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
        for (ScanResult r in results) {
          // Filter for TABLE WARS pucks (you can set a specific service UUID)
          if (r.device.platformName.contains('Puck') ||
              r.device.platformName.contains('TABLE_WARS')) {
            _addOrUpdatePuck(r);
          }
        }
      });

      // Auto-stop after timeout
      await Future.delayed(const Duration(seconds: 10));
      await stopScan();
    } catch (e) {
      debugPrint('Scan error: $e');
      _isScanning = false;
      notifyListeners();
    }
  }

  Future<void> stopScan() async {
    await FlutterBluePlus.stopScan();
    _scanSubscription?.cancel();
    _isScanning = false;
    notifyListeners();
  }

  void _addOrUpdatePuck(ScanResult result) {
    // Extract puck ID from name (e.g., "Puck_1" -> ID 1)
    int? puckId;
    final name = result.device.platformName;

    if (name.contains('_')) {
      final parts = name.split('_');
      puckId = int.tryParse(parts.last);
    }

    if (puckId == null) return;

    final existingIndex = _pucks.indexWhere((p) => p.id == puckId);

    if (existingIndex >= 0) {
      // Update existing puck
      _pucks[existingIndex] = _pucks[existingIndex].copyWith(
        device: result.device,
        rssi: result.rssi,
        isOnline: true,
        lastSeen: DateTime.now(),
      );
    } else {
      // Add new puck
      _pucks.add(PuckInfo(
        id: puckId,
        name: name,
        device: result.device,
        rssi: result.rssi,
        isOnline: true,
      ));
    }

    notifyListeners();
  }

  // ============================================================================
  // PUCK CONTROL
  // ============================================================================

  Future<bool> connectToPuck(int puckId) async {
    final puck = _pucks.firstWhere((p) => p.id == puckId);
    if (puck.device == null) return false;

    try {
      await puck.device!.connect(timeout: const Duration(seconds: 10));
      debugPrint('✅ Connected to Puck $puckId');
      return true;
    } catch (e) {
      debugPrint('❌ Connection failed: $e');
      return false;
    }
  }

  Future<void> disconnectFromPuck(int puckId) async {
    final puck = _pucks.firstWhere((p) => p.id == puckId);
    if (puck.device == null) return;

    try {
      await puck.device!.disconnect();
      debugPrint('Disconnected from Puck $puckId');
    } catch (e) {
      debugPrint('Disconnect error: $e');
    }
  }

  // ============================================================================
  // GAME CONTROL (via BLE characteristics - to be implemented)
  // ============================================================================

  Future<void> startGame(int puckId, String gameType) async {
    // TODO: Implement BLE characteristic write to start game
    debugPrint('Starting $gameType on Puck $puckId');

    // For now, just a placeholder
    // In real implementation, you'd write to a BLE characteristic
    /*
    final puck = _pucks.firstWhere((p) => p.id == puckId);
    if (puck.device != null && puck.device!.isConnected) {
      // Find the game control service
      List<BluetoothService> services = await puck.device!.discoverServices();
      for (var service in services) {
        if (service.uuid.toString() == 'YOUR_GAME_SERVICE_UUID') {
          for (var characteristic in service.characteristics) {
            if (characteristic.uuid.toString() == 'YOUR_GAME_CHAR_UUID') {
              // Write game command
              await characteristic.write([gameTypeCode]);
            }
          }
        }
      }
    }
    */
  }

  Future<void> stopAllGames() async {
    debugPrint('Stopping all games');
    // TODO: Broadcast stop command to all connected pucks
  }

  // ============================================================================
  // SERVER COMMUNICATION
  // ============================================================================

  void setServerUrl(String url) {
    _serverUrl = url;
    notifyListeners();
  }

  Future<Map<String, dynamic>?> fetchLeaderboard() async {
    // TODO: Implement HTTP request to server
    /*
    try {
      final response = await http.get(Uri.parse('$_serverUrl/api/leaderboard'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      debugPrint('Error fetching leaderboard: $e');
    }
    */
    return null;
  }

  // ============================================================================
  // UTILITIES
  // ============================================================================

  void removePuck(int puckId) {
    _pucks.removeWhere((p) => p.id == puckId);
    notifyListeners();
  }

  void clearAllPucks() {
    _pucks.clear();
    notifyListeners();
  }
}
