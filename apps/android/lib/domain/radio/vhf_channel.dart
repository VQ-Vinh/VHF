/// The marine VHF channel the Station's radio is on.
///
/// Nothing reports this yet: the Station captures audio from a device and has
/// no view of the radio's dial. Until it does, the value is simulated, and
/// [simulated] makes every place that shows it say so. Channel 16 is the
/// distress and calling channel, so an unlabelled 16 would be a claim about
/// safety the app cannot back.
class VhfChannel {
  const VhfChannel(this.number, {required this.simulated});
  final int number;
  final bool simulated;
}
