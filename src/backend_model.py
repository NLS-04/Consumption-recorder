from dataclasses    import dataclass
from datetime       import date
from math           import sqrt

from constants      import *
import dbWrapper as db


@dataclass
class Measurement:
    absolute : float | None
    mean     : float | None
    deviation: float | None
    
    minimum: float | date | None = None
    maximum: float | date | None = None

@dataclass
class Frame_statistics:
    readings_count: int
    
    days_stats: Measurement
    reading_attributes_stats: list[ Measurement ]

@dataclass
class Analyzed_month:
    month : int
    points: Frame_statistics

@dataclass
class Analyzed_year:
    year  : int
    points: Frame_statistics

@dataclass
class Analyzed_year_month:
    year  : int
    months: list[ Analyzed_month ]


class Analyze_Reading:
    """
    Statistically analyze a set of Readings by different criteria

    Readings can be analyzed:
        - in monthly frames grouped and ordered in years
        - in yearly  frames grouped and ordered in years
        - as single data frame
    """
    
    __readings : list[db.Reading]
    __year_ids : list[int]
    
    def __init__(self, readings: list[db.Reading] ) -> None:
        """
        Args:
            readings (`list[ db.Reading ]`): raw data directly from database
        """
        # sort all data entries by date (they usually are already in order, but we can not be sure)
        self.__readings = sorted( readings, key=lambda r: r.date )
        self.__year_ids = sorted( set( map(lambda r: r.date.year, readings) ) )
    
    def monthly(self) -> list[ Analyzed_year_month ]:
        """
        generate a list of monthly analyzed data-frame

        - Data is grouped by year and by month;
        - Only the month subgroups are statistically analyzed and summarized;

        Returns:
            `list[ Analyzed_year_month ]`: list of yearly grouped and monthly analyzed data
        """
        years = [ Analyzed_year_month( yr, [] ) for yr in self.__year_ids ]
        
        for year in years:
            readings_in_year = list( filter( lambda r: r.date.year == year.year, self.__readings ) )
            
            months: dict[int, list[db.Reading]] = dict()
            
            for reading in readings_in_year:
                if not reading.date.month in months.keys():
                    months[ reading.date.month ] = []
                
                months[ reading.date.month ].append( reading )
            
            
            # month_ids = list( map( lambda r: r.date.month, readings_in_year ) )
            # months = {
            #     m_id : 
            #     list( filter(lambda r: r.date.month == m_id, readings_in_year) ) for m_id in month_ids
            # }
            
            # filter out months with insufficient readings (needs at least 2, to calculate statistical data)
            months = dict( filter( lambda kv: len(kv[1]) > 1, months.items() ) )
            
            year.months = [
                Analyzed_month( 
                    month_id,
                    self._calculate_statistics(
                        points, 
                        date(year.year, month_id, 1), 
                        date(year.year, month_id+1, 1) if month_id < 12 else date(year.year+1, 1, 1) 
                    )
                )
                for month_id, points in months.items()
            ]
        
        return list( filter( lambda y: y.months, years ) )

    def yearly(self) -> list[ Analyzed_year ]:
        """
        generate a list of yearly analyzed data-frames

        - Data is grouped by year;
        - Data is, per annual group, statistically analyzed and summarized

        Returns:
            `list[ Analyzed_year ]`: list of yearly grouped and monthly analyzed data
        """
        
        out_list = []
        for year_id in self.__year_ids:
            points = list( filter( lambda r: r.date.year == year_id, self.__readings ) )

            out_list.append(
                Analyzed_year(
                    year_id,
                    self._calculate_statistics( points, date(year_id, 1, 1), date(year_id+1, 1, 1) )
                )
            )
        
        return out_list

    def completely(self) -> Frame_statistics:
        """
        generate statistic for the complete data-frame

        Returns:
            `Frame_statistics`: completely analyzed data-frame
        """
        
        return self._calculate_statistics( self.__readings )

    @staticmethod
    def _calculate_statistics(
        points:list[ db.Reading ],
        extrapolation_date_lower_bound:date=None,
        extrapolation_date_upper_bound:date=None
        ) -> Frame_statistics:
        """
        statistically analyze a set of reading points

        calculates the following for the total days and for each reading-attribute:
        - sum
        - mean
        - standard deviation
        - minimum
        - maximum
        
        IF `extrapolation_date_lower_bound` OR `extrapolation_date_upper_bound` are not `None`:
            The calculated data is extra-/interpolated to the given time span.
            Expect noisy values for insufficiently small time spans or insufficient amounts of data points.

        Args:
            points (`list[ db.Reading ]`): raw data directly from database
            extrapolation_date_lower_bound (`date`, optional): lower bound for extra-/interpolation. Defaults to None.
            extrapolation_date_upper_bound (`date`, optional): upper bound for extra-/interpolation. Defaults to None.

        Returns:
            `Frame_statisticss`: statistically analyzed data points
        """
        
        amount_points = len(points)
        
        if amount_points < 2:
            return Frame_statistics( 0, Measurement(0, 0, 0), [Measurement(0, 0, 0)]*COUNT_READING_ATTRIBUTES )
        
        extrapolation_date_lower_bound = extrapolation_date_lower_bound if extrapolation_date_lower_bound else points[0].date
        extrapolation_date_upper_bound = extrapolation_date_upper_bound if extrapolation_date_upper_bound else points[-1].date
        
        
        delta_d, total_d, sum_stats_d, sum_stats_sqr_d = 0.0, 0.0, 0.0, 0.0
        mean_d, deviation_d = 0.0, None
        
        delta           : list[float]      = [0.0]  * COUNT_READING_ATTRIBUTES
        total           : list[float|None] = [0.0]  * COUNT_READING_ATTRIBUTES
        sum_stats       : list[float|None] = [0.0]  * COUNT_READING_ATTRIBUTES
        sum_stats_sqr   : list[float|None] = [0.0]  * COUNT_READING_ATTRIBUTES
        gap             : list[int]        = [0]    * COUNT_READING_ATTRIBUTES
        
        included_points : list[int]        = [0]    * COUNT_READING_ATTRIBUTES
        first_point_date: list[date]       = [None] * COUNT_READING_ATTRIBUTES
        last_point_date : list[date]       = [None] * COUNT_READING_ATTRIBUTES
        
        mean            : list[float|None] = [None] * COUNT_READING_ATTRIBUTES
        deviation       : list[float|None] = [None] * COUNT_READING_ATTRIBUTES
        
        # like extrapolation_date_lower_bound, extrapolation_date_upper_bound
        # set these lower and upper bound for each value individually
        for k in range(COUNT_READING_ATTRIBUTES):
            for r in points:
                if not r.attributes[k]:
                    continue
                
                if not first_point_date[k]:
                    first_point_date[k] = r.date
                
                last_point_date[k] = r.date
        
        # different edge cases may occur while analyzing the data. All possible edge cases are listed below as examples and are accounted for in the code below
        # day |    case 1     |     case 2     |      case 3     |      case 4     |      case 5     |      case 6     |      case 7     |
        #     | reader reset  |  missing point |  missing point  |  missing point  |  missing point  |  missing point  |  missing point  |
        #     |               |                | + reader reset  | + missing point | + reader reset  |                 | + missing point |
        # ----|---------------|----------------|-----------------|-----------------|-----------------|-----------------|-----------------|
        #  0  |    100.0      |     100.0      |     100.0       |      None       |     100.0       |      None       |      None       |
        #  1  |    200.0      |     200.0      |      None       |      None       |      None       |     200.0       |      None       |
        #  2  |      0.0      |      None      |       0.0       |     100.0       |       0.0       |       ---       |       ---       |
        #  3  |    100.0      |     400.0      |     100.0       |     200.0       |       ---       |       ---       |       ---       |
        
        
        for i in range(1, len(points)):
            r = points[i]
            
            delta_d          = (r.date - points[i-1].date).days
            total_d         += delta_d
            sum_stats_d     += delta_d
            sum_stats_sqr_d += delta_d ** 2
            
            # iterate over all reading value objs
            for k in range( COUNT_DIGIT_OBJS ):
                # implicitly catches case 7
                if r.attributes[k] is None:
                    continue
                
                earlier_v = None
                n = (i-1)+1

                # search for an earlier value to calculate a delta value
                # catches case 2, 3, 5
                while (n:=n-1) >= 0:
                    earlier_v = points[n].attributes[k]
                    if earlier_v:
                        delta[k] = r.attributes[k] - earlier_v
                        break
                
                # we are not able to calculate a data value if all previous values are None
                # catches case 4, 6
                if earlier_v is None:
                    continue
                
                ddays = ( r.date - points[n].date ).days
                
                # to correct for large negative values, e.g. because a meter got changed and was reseted to 0 or other faulty data
                # in this context we usually expect positive changes, i.e. strictly monotonic increasing data points
                # therefor we reject negative deltas and do not include that time span (and values)
                # case 1
                if delta[k] < 0:
                    gap[k] += ddays
                    continue
                
                included_points[k] += 1
                
                total[k]         += delta[k]
                sum_stats[k]     += delta[k] / ddays
                sum_stats_sqr[k] += (delta[k] / ddays) ** 2
        
        # ------------------------------------------------------------------------------------------------------------------------------------------
        # mean and deviation are measured in respect to the change of value per day
        # since we measure a "derivative" we "loose" one data point and thus need to reduce our number of points by one ( similar to z-Transform )
        # ------------------------------------------------------------------------------------------------------------------------------------------
        mean_d = sum_stats_d / ( amount_points - 1 )
        if amount_points > 2:
            deviation_d = sqrt( ( sum_stats_sqr_d - ( amount_points - 1 ) * ( mean_d**2 ) ) / ( amount_points - 2 ) )
        
        for k in range( COUNT_READING_ATTRIBUTES ):
            if included_points[k] <= 0:
                total[k] = None
                continue
            
            mean[k] = sum_stats[k] / included_points[k]
            
            if included_points[k] > 1:
                deviation[k] = sqrt( ( sum_stats_sqr[k] - included_points[k] * ( mean[k]**2 ) ) / ( included_points[k] - 1 ) )
            
            extra_days = ( first_point_date[k] - extrapolation_date_lower_bound ).days + ( extrapolation_date_upper_bound - last_point_date[k] ).days
            
            # adjust each value for gaps (negative delta) and days to be extrapolated in the data points
            total[k] += ( gap[k] + extra_days ) * mean[k]
        
        
        return Frame_statistics(
            amount_points,
            Measurement( total_d, mean_d, deviation_d, extrapolation_date_lower_bound, extrapolation_date_upper_bound ),
            [ 
                Measurement(
                    total[k],
                    mean[k],
                    deviation[k],
                    min( filter( lambda r: r.attributes[k] is not None, points ), key=lambda r: r.attributes[k] ),
                    max( filter( lambda r: r.attributes[k] is not None, points ), key=lambda r: r.attributes[k] )
                )
                for k in range( COUNT_READING_ATTRIBUTES )
            ]
        )

