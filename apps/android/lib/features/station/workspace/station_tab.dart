enum StationTab {
  control,
  live;

  StationPage get page => switch (this) {
    control => StationPage.control,
    live => StationPage.live,
  };
}

/// Route destinations include secondary pages, independently of the tab bar.
enum StationPage {
  control,
  live,
  history,
  settings;

  StationTab? get primaryTab => switch (this) {
    control => StationTab.control,
    live => StationTab.live,
    history || settings => null,
  };

  /// Anything unknown lands on Control, which is also where a saved
  /// /stations/:id/dashboard link from before the tabs merged now goes.
  static StationPage fromPath(String? value) =>
      values.firstWhere((page) => page.name == value, orElse: () => control);
}
