import tkinter as tk
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)


class CounterAndScanner:
    def __init__(self, rate_counter, wavelength_controller) -> None:

        self.running = False
        self.current_t = 0
        self.vmin = float(wavelength_controller.minimum_allowed_position)
        self.vmax = float(wavelength_controller.maximum_allowed_position)
        self.tmax = 100
        self._step_size = 0.5
        self.raster_line_pause = 0.150  # wait 150ms for the voltage to settle before a line scan

        self.scanned_raw_counts = []
        self.scanned_count_rate = []

        self.wavelength_controller = wavelength_controller
        self.rate_counter = rate_counter
        self.num_daq_batches = 1  # could change to 10 if want 10x more samples for each position

    def stop(self) -> None:
        self.rate_counter.stop()
        self.running = False

    def start(self) -> None:
        self.running = True
        self.rate_counter.start()

    def set_to_starting_position(self) -> None:
        self.current_v = self.vmin
        if self.wavelength_controller:
            self.wavelength_controller.go_to_voltage(v=self.vmin)

    def close(self) -> None:
        self.rate_counter.close()

    def set_num_data_samples_per_batch(self, N) -> None:
        self.rate_counter.num_data_samples_per_batch = N

    def sample_counts(self) -> np.ndarray:
        return self.rate_counter.sample_counts(self.num_daq_batches)

    def sample_count_rate(self, data_counts=None) -> np.floating:
        if data_counts is None:
            data_counts = self.sample_counts()
        return self.rate_counter.sample_count_rate(data_counts)

    def set_scan_range(self, vmin, vmax) -> None:
        if self.wavelength_controller:
            self.wavelength_controller.check_allowed_position(vmin)
            self.wavelength_controller.check_allowed_position(vmax)
        self.vmin = vmin
        self.vmax = vmax

    def get_scan_range(self) -> tuple:
        """
        Returns a tuple of the full scan range
        :return: xmin, xmax, ymin, ymax
        """
        return self.vmin, self.vmax,

    def get_completed_scan_range(self) -> tuple:
        """
        Returns a tuple of the scan range that has been completed
        :return: xmin, xmax, ymin, current_y
        """
        return self.vmin, self.vmax, self.current_v

    def still_scanning(self) -> None:
        if self.running == False:  # this allows external process to stop scan
            return False

        if self.current_t <= self.tmax:  # stops scan when reaches final position
            return True
        else:
            self.running = False
            return False

    def move_v(self) -> None:
        self.current_v += self._step_size
        if self.wavelength_controller and self.current_v <= self.vmax:
            try:
                self.wavelength_controller.go_to_position(v=self.current_v)
            except ValueError as e:
                logger.info(f'out of range\n\n{e}')

    def go_to_v(self, desired_voltage) -> None:
        if self.wavelength_controller and desired_voltage <= self.vmax and desired_voltage >= self.vmin:
            try:
                self.wavelength_controller.go_to_voltage(v=desired_voltage)
            except ValueError as e:
                logger.info(f'out of range\n\n{e}')

    def scan_v(self) -> None:
        """
        Scans the wavelengths from vmin to vmax in steps of step_size.

        Stores results in self.scanned_raw_counts and self.scanned_count_rate.
        """
        raw_counts_for_axis = self.scan_axis('v', self.vmin, self.vmax, self._step_size)
        self.scanned_raw_counts.append(raw_counts_for_axis)
        self.scanned_count_rate.append([self.sample_count_rate(raw_counts) for raw_counts in raw_counts_for_axis])
        self.current_t = self.current_t + 1

    def scan_axis(self, axis, min, max, step_size) -> list:
        """
        Moves the stage along the specified axis from min to max in steps of step_size.
        Returns a list of raw counts from the scan in the shape
        [[[counts, clock_samples]], [[counts, clock_samples]], ...] where each [[counts, clock_samples]] is the
        result of a single call to sample_counts at each scan position along the axis.
        """
        raw_counts = []
        self.wavelength_controller.go_to_voltage(**{axis: min})
        time.sleep(self.raster_line_pause)
        for val in np.arange(min, max, step_size):
            if self.wavelength_controller:
                logger.info(f'go to voltage {axis}: {val:.2f}')
                self.wavelength_controller.go_to_voltage(**{axis: val})
            _raw_counts = self.sample_counts()
            raw_counts.append(_raw_counts)
            logger.info(f'raw counts, total clock samples: {_raw_counts}')
            if self.wavelength_controller:
                logger.info(f'current voltage: {self.wavelength_controller.get_current_voltage()}')

        return raw_counts

    def reset(self) -> None:
        self.scanned_raw_counts = []
        self.scanned_count_rate = []

    def configure_view(self, gui_root: tk.Toplevel) -> None:
        """
        This method launches a GUI window to configure the controller.
        """
        pass

    @property
    def step_size(self):
        return self._step_size
    @step_size.setter
    def step_size(self, val):
        self._step_size = val



