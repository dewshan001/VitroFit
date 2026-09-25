import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

/// Uses the existing ASP.NET identity system; Python is never a mobile endpoint.
class FitnessApi {
  static const baseUrl = String.fromEnvironment('FITNESS_API_BASE_URL',
      defaultValue: 'http://10.0.2.2:5284/api');
  static const _tokenKey = 'vitrofit_fitness_access_token';
  final http.Client client;
  final FlutterSecureStorage storage;

  FitnessApi({http.Client? client, FlutterSecureStorage? storage})
      : client = client ?? http.Client(),
        storage = storage ?? const FlutterSecureStorage();

  Future<bool> hasSession() async => (await storage.read(key: _tokenKey)) != null;
  Future<void> logout() => storage.delete(key: _tokenKey);
  void close() => client.close();

  Future<void> login(String email, String password) async {
    final data = await _send('auth/login', method: 'POST', body: {'email': email, 'password': password});
    final token = data['accessToken'];
    if (token is! String || token.isEmpty) throw Exception('Invalid sign-in response.');
    await storage.write(key: _tokenKey, value: token);
  }

  Future<dynamic> request(String path, {String method = 'GET', Object? body}) =>
      _send('fitness/$path', method: method, body: body);

  Future<dynamic> _send(String path, {String method = 'GET', Object? body}) async {
    final token = await storage.read(key: _tokenKey);
    final request = http.Request(method, Uri.parse('$baseUrl/$path'));
    request.headers['Content-Type'] = 'application/json';
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    if (body != null) request.body = jsonEncode(body);
    final response = await (() async => http.Response.fromStream(await client.send(request)))()
        .timeout(const Duration(seconds: 150));
    dynamic data;
    try { data = jsonDecode(response.body); } catch (_) { data = <String, dynamic>{}; }
    if (response.statusCode == 401) {
      await logout();
      throw Exception('Session expired. Sign out and sign in again.');
    }
    if (response.statusCode >= 400) {
      throw Exception(data is Map ? data['message'] ?? data['error'] ?? 'Check your input or try again.' : 'Request failed.');
    }
    return data;
  }
}
