# Extracted Features

All the extracted features, in aggregated format, can be found in the files [extracted_features_final.xlsx](https://github.com/SARAI-Lab-KIT/emotion-study-pdf/blob/main/extracted_features/extracted_features.xlsx) or [extracted_features_final.csv](https://github.com/SARAI-Lab-KIT/emotion-study-pdf/blob/main/extracted_features/extracted_features.csv).

Below, you will find a list describing each extracted feature. The features were extracted from the participants' drawing logs collected in real time by the tablet ROS2 node and from the final version of the participants' drawing.

| Feature                                  | Extracted from     |    Description  |
| :--- | :--- | :--- |
| n_strokes | Tool usage | number of strokes with the pen tool that weren't removed using the undo tool |
| n_eraser_strokes | Tool usage | number of strokes with the eraser tool that weren't removed using the undo tool |
| n_undone_strokes | Tool usage | number of strokes with the pen or eraser tool that were removed using the undo tool |
| pen_size_used_count | Tool usage | number of distinct pen sizes used |
| pen_size_mean | Tool usage | average pen size of strokes |
| pen_size_std | Tool usage | variability in stroke pen size |
| bbox_width | Global spatial | width of the bounding box enclosing the drawing |
| bbox_height | Global spatial | height of the bounding box enclosing the drawing |
| bbox_area | Global spatial | area of the bounding box enclosing the drawing |
| centroid_x | Global spatial | horizontal position of the drawing's center of mass |
| centroid_y | Global spatial | vertical position of the drawing's center of mass |
| spatial_spread | Global spatial | overall dispersion of drawn points around the centroid |
| ink_density | Global spatial | amount of ink (stroke length) relative to the bounding box area |
| bbox_aspect_ratio | Global spatial | ratio of bounding box width to height |
| bbox_diagonal | Global spatial | diagonal length of the bounding box, an overall size measure |
| bbox_elongation | Global spatial | normalized measure of how far the bounding box is from square |
| stroke_total_length | Kinematics | cumulative length of all strokes |
| stroke_mean_length | Kinematics | average length of strokes |
| stroke_std_length | Kinematics | variability in stroke lengths |
| stroke_mean_speed | Kinematics | average speed of strokes |
| stroke_std_speed | Kinematics | variability in stroke speed |
| stroke_mean_accel | Kinematics | average acceleration of strokes |
| stroke_std_accel | Kinematics | variability in stroke acceleration |
| speed_dominant_freq | Kinematics | dominant frequency of the stroke speed signal |
| speed_dominant_freq_power | Kinematics | relative spectral power at the dominant speed frequency |
| stroke_speed_trend | Kinematics | linear trend in stroke speed over the course of the drawing |
| stroke_speed_half_diff | Kinematics | difference in average speed between the second and first half of the drawing |
| stroke_length_trend | Kinematics | linear trend in stroke length over the course of the drawing |
| stroke_length_half_diff | Kinematics | difference in average stroke length between the second and first half of the drawing |
| speed_peaks_per_sec | Kinematics | rate of local speed reversals (accelerations/decelerations) per second |
| speed_distance_to_mean | Kinematics | distance between this drawing's speed spectrum and the population-average speed spectrum |
| avg_time_between_strokes | Timing | average time between strokes |
| std_time_between_strokes | Timing | variability of inter-stroke intervals |
| total_pause_time | Timing | total inter-stroke intervals time |
| pause_ratio | Timing | ratio between total_pause_time and activity_time |
| stroke_frequency | Timing | rate of strokes over time |
| stroke_mean_curvature | Stroke complexity | average curvature of strokes |
| stroke_mean_angularity | Stroke complexity | average sharpness/angle of strokes |
| stroke_mean_straightness | Stroke complexity | average ratio of straight-line displacement to path length per stroke |
| stroke_std_straightness | Stroke complexity | variability in stroke straightness |
| stroke_straightness_trend | Stroke complexity | linear trend in stroke straightness over the course of the drawing |
| stroke_mean_abs_jerk | Stroke complexity | average magnitude of jerk (rate of change of acceleration), reflecting movement erraticism |
| stroke_speed_zero_cross_rate | Stroke complexity | rate of local speed reversals per second, a smoothness/tremor proxy |
| trajectory_fractal_dimension | Stroke complexity | box-counting fractal dimension of the pen trajectory, reflecting path complexity |
| stroke_mean_pressure | Pressure | average pressure of strokes |
| stroke_std_pressure | Pressure | variability in stroke pressure |
| stroke_pressure_slope | Pressure | slope of pressure change over time |
| pressure_velocity_corr | Pressure | correlation between pen speed and pressure within strokes |
| pressure_change_bandwidth | Pressure | spread of frequencies (90% band) in the speed-of-pressure-change signal |
| pressure_change_median_freq | Pressure | power-weighted median frequency of the speed-of-pressure-change signal |
| pressure_change_peaks_per_sec | Pressure | rate of local reversals in the speed-of-pressure-change signal per second |
| pressure_change_distance_to_mean | Pressure | distance between this drawing's pressure-change spectrum and the population-average spectrum |
| tilt_x_mean | Tilt | average pen tilt along the x-axis |
| tilt_y_mean | Tilt | average pen tilt along the y-axis |
| tilt_x_std | Tilt | variability in pen tilt along the x-axis |
| tilt_y_std | Tilt | variability in pen tilt along the y-axis |
| tilt_pressure_corr | Tilt | correlation between pen tilt and pressure within strokes |
| tiltx_change_bandwidth | Tilt | spread of frequencies (90% band) in the speed-of-tilt-x-change signal |
| tiltx_change_median_freq | Tilt | power-weighted median frequency of the speed-of-tilt-x-change signal |
| tiltx_change_peaks_per_sec | Tilt | rate of local reversals in the speed-of-tilt-x-change signal per second |
| tiltx_change_distance_to_mean | Tilt | distance between this drawing's tilt-x-change spectrum and the population-average spectrum |
| tilty_change_bandwidth | Tilt | spread of frequencies (90% band) in the speed-of-tilt-y-change signal |
| tilty_change_median_freq | Tilt | power-weighted median frequency of the speed-of-tilt-y-change signal |
| tilty_change_peaks_per_sec | Tilt | rate of local reversals in the speed-of-tilt-y-change signal per second |
| tilty_change_distance_to_mean | Tilt | distance between this drawing's tilt-y-change spectrum and the population-average spectrum |
| tilt_magnitude_mean | Tilt | average overall steepness of pen tilt, combining both axes |
| tilt_magnitude_std | Tilt | variability in overall pen tilt steepness |
| tilt_angle_mean | Tilt | average direction of pen lean (circular mean of tilt angle) |
| tiltx_trend | Tilt | linear trend in pen tilt (x-axis) over the course of the drawing |
| tilty_trend | Tilt | linear trend in pen tilt (y-axis) over the course of the drawing |
| surface_coverage_ratio | Global spatial (from image) | proportion of canvas area covered by drawing |
| pixel_std_x | Global spatial (from image) | horizontal dispersion of drawn pixels |
| pixel_std_y | Global spatial (from image) | vertical dispersion of drawn pixels |
| mean_distance_center | Global spatial (from image) | average distance of drawing elements from canvas center |
| left_right_balance | Global spatial (from image) | balance of content between left and right sides |
| top_bottom_balance | Global spatial (from image) | balance of content between top and bottom sides |
| colors_used_count | Color | number of distinct colors used |
| mean_hue | Color | average hue value of colors used |
| std_hue | Color | variability in hue values |
| mean_saturation | Color | average saturation of colors used |
| std_saturation | Color | variability in saturation values |
| mean_brightness | Color | average brightness of colors used |
| std_brightness | Color | variability in brightness values |
| black_ratio | Color | ratio between black pixels and non-black pixels, excluding white background |
| warm_cool_ratio | Color | ratio between warm and cool pixels based on hue, excluding white background |
| brightness_range | Color | spread between high and low brightness percentiles, reflecting contrast |
