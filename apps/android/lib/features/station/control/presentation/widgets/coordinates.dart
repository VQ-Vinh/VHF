/// Degrees, minutes and seconds, the way a fix is read off a GPS.
///
/// The hemisphere comes from the sign rather than a minus sign, and the
/// seconds are rounded before the minutes are carried, so 10.99999 reads as
/// 11°00'00" and never as 10°59'60".
String formatDms(
  double value, {
  required String positive,
  required String negative,
}) {
  final hemisphere = value < 0 ? negative : positive;
  final total = (value.abs() * 3600).round();
  final degrees = total ~/ 3600;
  final minutes = (total % 3600) ~/ 60;
  final seconds = total % 60;
  return "$degrees°${minutes.toString().padLeft(2, '0')}'"
      '${seconds.toString().padLeft(2, '0')}"$hemisphere';
}
