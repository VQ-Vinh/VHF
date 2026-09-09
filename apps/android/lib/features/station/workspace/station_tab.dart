enum StationTab {
  dashboard,
  control,
  live;

  StationPage get page => switch (this) {
    dashboard => StationPage.dashboard,
    control => StationPage.control,
    live => StationPage.live,
  };
}

/// Route destinations include secondary pages, independently of the tab bar.
enum StationPage {
  dashboard,
  control,
  live,
  history,
  settings;

  StationTab? get primaryTab => switch (this) {
    dashboard => StationTab.dashboard,
    control => StationTab.control,
    live => StationTab.live,
    history || settings => null,
  };

  static StationPage fromPath(String? value) =>
      values.firstWhere((page) => page.name == value, orElse: () => dashboard);
}
