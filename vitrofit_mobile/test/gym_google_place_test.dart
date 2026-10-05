import 'package:flutter_test/flutter_test.dart';
import 'package:vitrofit_mobile/api/google_places_api.dart';
import 'package:vitrofit_mobile/models/gym.dart';

void main() {
  group('Gym.fromGooglePlace', () {
    final place = {
      'id': 'ChIJabc',
      'displayName': {'text': 'Zest Gym', 'languageCode': 'en'},
      'formattedAddress': '12 Main St, Colombo',
      'location': {'latitude': 6.93, 'longitude': 79.86},
      'websiteUri': 'https://zest.example',
      'nationalPhoneNumber': '011 234 5678',
    };

    test('maps every field and computes the distance from the search centre', () {
      final gym = Gym.fromGooglePlace(place, originLat: 6.9271, originLng: 79.8612)!;
      expect(gym.placeId, 'ChIJabc');
      expect(gym.name, 'Zest Gym');
      expect(gym.address, '12 Main St, Colombo');
      expect(gym.website, 'https://zest.example');
      expect(gym.phone, '011 234 5678');
      expect(gym.distanceMeters, inInclusiveRange(250, 450));
    });

    test('leaves the distance empty without an origin and defaults the name', () {
      final gym = Gym.fromGooglePlace({
        'id': 'x',
        'location': {'latitude': 1.0, 'longitude': 2.0},
      })!;
      expect(gym.distanceMeters, isNull);
      expect(gym.name, 'Unnamed gym');
      expect(gym.website, isNull);
    });

    test('skips places without an id or a location', () {
      expect(Gym.fromGooglePlace({'displayName': {'text': 'a'}}), isNull);
      expect(Gym.fromGooglePlace({'id': 'x'}), isNull);
    });
  });

  test('haversineMeters is about 111 km per degree of latitude', () {
    expect(haversineMeters(0, 0, 1, 0), closeTo(111195, 300));
    expect(haversineMeters(6.9, 79.8, 6.9, 79.8), 0);
  });
}
