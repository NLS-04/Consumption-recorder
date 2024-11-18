from __future__ import annotations

from typing         import Final, NamedTuple, Self, Callable, Iterable, TypeAlias
from dataclasses    import dataclass
from datetime       import date, timedelta
from math           import sqrt, ceil, floor

from generic_lib.utils import *
from constants   import *
import dbWrapper as db

_FLAG_DEBUG_PRINTS_SECTION_SOLVER: Final[bool] = False

DBG_PRINT: Callable[..., None] = print if _FLAG_DEBUG_PRINTS_SECTION_SOLVER else lambda *x, **y: None


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
            `Frame_statistics`: statistically analyzed data points
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




class Contribution:
    _contrib: dict[db.Person, float]
    
    def sum(self) -> float:
        return sum( self._contrib.values() )
    def normalize(self) -> Contribution:
        mag = self.sum()
        
        return self * (1/mag) if mag else self * 0.0
    
    def __init__(self, *person_contrib:db.Person|float|tuple[db.Person, float] ) -> None:
        is_flatten = all( map( lambda pc: isinstance(pc, db.Person), person_contrib[0::2] ) ) and all( map( lambda pc: isinstance(pc, (float, int)), person_contrib[1::2] ) )
        
        if not is_flatten:
            is_tuples  = all( map( lambda pc: isinstance(pc[0], db.Person) and isinstance(pc[1], (float, int)), person_contrib ) )
            assert is_tuples or is_flatten, "input sequence is invalid: only valid types are Iterable[db.Person, float, ...] or Iterable[tuple[db.Person, float], ...]"
        
        if is_flatten:
            self._contrib = { p: c for p, c in zip(person_contrib[0::2], person_contrib[1::2]) }
        else:
            self._contrib = { p: c for p, c in person_contrib }
    
    def __getitem__(self, key:db.Person) -> float:
        assert isinstance(key, db.Person), TypeError()
        
        return self._contrib[key] if key in self._contrib else 0.0
    def __setitem__(self, key:db.Person, value:float) -> float:
        assert isinstance(key, db.Person), TypeError()
        assert isinstance(value, (float, int)), TypeError()
        
        self._contrib[key] = value
        
        return value
    def __iter__(self) -> Iterable[tuple[db.Person, float]]:
        return ((p, c) for p, c in self._contrib.items())
    
    def __mul__(self, __x:int|float) -> Contribution:
        assert isinstance(__x, (float, int)), TypeError()
        
        return Contribution( *( (p, c * __x) for p, c in self._contrib.items() ) )
    def __imul__(self, __x: int|float) -> Self:
        assert isinstance(__x, (float, int)), TypeError()
        
        for p in self._contrib.keys():
            self._contrib[p] *= __x
        
        return self
    __rmul__ = __mul__
    
    def __add__(self, __other:Contribution) -> Contribution:
        assert isinstance( __other, Contribution ), TypeError()
        
        contrib = Contribution( *self )
        
        for p, c in __other.__iter__():
            contrib[p] += c
        
        return contrib
    def __iadd__(self, __other: Contribution) -> Self:
        assert isinstance( __other, Contribution ), TypeError()
        
        for p, c in __other.__iter__():
            self[p] += c
        
        return self
    __radd__ = __add__

class Section_Node():
    date_range: Dates_Delta
    sub_nodes : list[Section_Node]
    
    def __init__( self, date_range: Dates_Delta ) -> None:
        self.date_range = date_range
        self.sub_nodes = []

class Section_Person_Solver( Section_Node ):
    sub_nodes: list[Section_Person_Solver]
    manages_person: db.Person | None
    
    
    def __init__(self, date_range: Dates_Delta, manages_person:db.Person=None) -> None:
        super().__init__(date_range)
        self.manages_person = manages_person
    
    def solve(self, persons_to_sectionize: list[db.Person]) -> Section_Person_Solver:
        """
        ### Create a dynamic B-tree of sectionized persons.
        
        Each node represents a distinct section of a persons date-range (i.e. inhabitants time-range).

        Each node recursively subdivides its date-range into subnodes, propagating persons and responsibilities accordingly

        Args:
            persons_to_sectionize (`list[db.Person]`):  list of persons to be sectionized.
                                                        > attention: each person must have valid `move_in` and `move_out` dates where `move_in` <= `move_out` !

        Returns:
            `Section_Person_Solver`: constructed B-tree of subdivided person sections
        """

        if self.date_range.days <= 0:
            return self
        
        propagate_list: list[db.Person] = sorted( persons_to_sectionize, key=lambda p: p.move_out - p.move_in, reverse=True )
        
        
        intersect    : Intersection = Intersection.DISJOINT
        p_date_range : Dates_Delta

        search_person: db.Person
        search_index : int          = -1
        
        while intersect == Intersection.DISJOINT and search_index < len(propagate_list)-1:
            search_index  += 1
            search_person  = propagate_list[search_index]
            
            p_date_range = Dates_Delta( search_person.move_in, search_person.move_out )
            intersect    = self.date_range.intersect( p_date_range )
        
        
        match intersect:
            case Intersection.DISJOINT:
                # Intersection Layout:
                #   |-this-|
                #             |--p--|
                pass
            
            case Intersection.EQUAL | Intersection.SUB_SET:
                # Intersection Layout:
                #   |-this-|
                #   |---p--|
                # or
                # Intersection Layout:
                #   |-this-|
                # |-----p-----|
                
                # person p completely covers this section
                # => no earlier or later sections
                
                if not self.manages_person:
                    self.manages_person = search_person
                    self.sub_nodes = [ Section_Person_Solver( self.date_range ) ]
                else:
                    self.sub_nodes = [ Section_Person_Solver( self.date_range, search_person ) ]
            
            case Intersection.SUPER_SET:
                # Intersection Layout:
                #  |-----this-----|
                #    |--p--|
                
                # person p completely contained by this section
                # => split date range up into 3 sections
                
                self.sub_nodes = [
                    Section_Person_Solver( Dates_Delta( self.date_range.date_low, search_person.move_in - timedelta(1) ) ),
                    Section_Person_Solver( p_date_range, search_person ),
                    Section_Person_Solver( Dates_Delta( search_person.move_out + timedelta(1), self.date_range.date_high ) )
                ]
            
            case Intersection.PARTIAL_OVERLAP_LEFT:
                # Intersection Layout:
                #     |---this---|
                #  |----p----|
                
                # person p partially contained by this section
                # => split date range up into 2 sections
                
                self.sub_nodes = [
                    Section_Person_Solver( Dates_Delta( self.date_range.date_low, search_person.move_out ), search_person ),
                    Section_Person_Solver( Dates_Delta( search_person.move_out + timedelta(1), self.date_range.date_high ) )
                ]
            
            case Intersection.PARTIAL_OVERLAP_RIGHT:
                    # Intersection Layout:
                    #  |---this---|
                    #      |----p----|
                    
                    # person p partially contained by this section
                    # => split date range up into 2 sections
                    
                    self.sub_nodes = [
                        Section_Person_Solver( Dates_Delta( self.date_range.date_low, search_person.move_in - timedelta(1) ) ),
                        Section_Person_Solver( Dates_Delta( search_person.move_in, self.date_range.date_high ), search_person )
                    ]
        
        
        self.sub_nodes = [ n.solve( propagate_list[search_index+1::] ) for n in self.sub_nodes ]
        
        
        return self
    
    def simplify(self) -> Self | None:
        """
        ### simplify and prepare the tree structure to be used for the distribution calculation

        transforming following aspects:
            - identifying and structurally removing children-less and non person managing leaf nodes
            - propagating subnodes upwards for unnamed nodes (meaning nodes not responsible for any person)
        

        Returns:
            `Self | None`: simplified sub-tree structure none if children-less leave nodes 
        """
        
        if self.date_range.days <= 0:
            return None
        
        self.sub_nodes = list( filter( None, (sub.simplify() for sub in self.sub_nodes) ) )

        if not self.manages_person:
            sub_count = len(self.sub_nodes)
            if sub_count == 0:
                return None
            if sub_count == 1:
                return self.sub_nodes[0]

        for sub in self.sub_nodes[::]:
            if sub.manages_person:
                continue
            
            if not sub.sub_nodes:
                sub.manages_person = self.manages_person
            else:
                self.sub_nodes.remove( sub )
                self.sub_nodes.extend( sub.sub_nodes )
        
        return self
    
    def assert_valid_solver_tree_structure(self) -> None:
        """
        ### validate the B-tree to be used for distribution calculation

        usually used to validate simplified trees
        
        ---
        required validation criteria for each tree/node are as follows:
            - date_range must be strictly positive
            - `manages_person` must not be None, i.e. node must be responsible for a person
            - validity of subtrees (if any)
            - date-ranges of all subtrees (if any) must not be partially or completely outside of the date-range of the parent node
        """
        
        if self.date_range.days <= 0:
            # ranges must be strictly positive
            raise ValueError( f"date-range in days is {self.date_range.days} but must be positive" )
        
        if not self.manages_person:
            # unnamed, i.e. not responsible nodes are invalid
            raise ValueError( f"Node does not manage any person" )
            
        for sub in self.sub_nodes:
            match self.date_range.intersect( sub.date_range ):
                case Intersection.EQUAL | Intersection.SUPER_SET:
                    pass
                case _ as intersect:
                    # subtrees must not overlap more than the local root
                    raise ValueError( f"Intersection of the parents date-range and a subtrees is {intersect}, but must only be either Intersection.EQUAL or Intersection.SUPER_SET" )
    
    def calculate_contributions(self) -> Contribution:
        """
        ### calculate the correct distribution of a valid sectionized B-tree
        
        #### attention: tree must be valid or otherwise this algorithm will result in undefined behavior
        
        ---
        #### The problem can mathematically be modeled as a B-Tree with weighted Nodes.
        
        Each Node `N[i]` of the B-Tree (with total node count `n`) consists of:
            - a local State `X0[i]`;
            - `b`-many weighted children Nodes `( N[ b*i + 1 ], N[ b*i + 2 ], ..., N[ b*i + b ] )` ;
            - weights `( w[1], w[2], ... w[b])` where `sum[1 <= k <= b]( w[k] ) € {0, 1}`.
        
        The absolute State `X[i]` of a Node `N[i]` is determined by the recursive equation:
            `X[i] := 0.5 * ( X0[i] + sum[1 <= k <= b]( w[k] * X[b*i + k] ) )`
        
        #### Constraints and Design:

        1. A State `X[i]` of a Node `i` is a `p`-dimensional vector where `X[i][q]` with index `1 <= q <= p` is the distribution value of person `q` for that Node
        2. All States `X` must be normalized! A Node `i` is normalized if `sum[1 <= j <= p]( X[i][j] ) == 1`
        3. A local State `X0[i]` of a Node `i` must be of the form: `X0[i] := { delta[q,0], delta[q,1], ... delta[q,q], ... delta[q,p] }` where `delta[n,m] := {  1   if n==m,  0   if n!=m`
        4. Leaf Nodes are Nodes with weights `w[k] = 0 for all k in [1; b]` and therefore satisfy as a break condition for recursive equations
        """
        
        contrib : Contribution = Contribution()
        coverage: float        = 0.0
        for sub in self.sub_nodes:
            scale = sub.date_range.days / self.date_range.days
            coverage += scale
            
            contrib += scale * sub.calculate_contributions()
        
        contrib[self.manages_person] += 1 + ( 1 - coverage )
        contrib *= 0.5
        
        return contrib
    
    
    @classmethod
    def visualize(cls, section_to_visualize:Section_Person_Solver, add_time_line:bool=False, min_string_width:int=0, max_string_width:int=None) -> str:
        """
        ### visualize a Section tree as a bar like graph

        ---
        #### Layout
        a tree of the pseudo structure
        >>> DD(A, E)        Person_A
        >>> |  DD(C, F)     Person_B
        >>> |  DD(A, D)     Person_C
        >>> |  |  DD(B, D)  Person_D
        
        would be visualized with a time line like this:
        >>> [-------------------Person_A-------------------]             
        >>>                         [-------------Person_B-------------] 
        >>> [-------------Person_C-------------]                         
        >>>             [-------Person_D-------]                         
        >>> |           |           |           |           |           |
        >>> A           B           C           D           E           F
        

        Args:
            section_to_visualize (`Section_Person_Solver`): tree to visualize
            add_time_line (`bool`, optional): iff True appends a correctly scaled and placed time line at the bottom of the visualization. Defaults to False.
            min_string_width (`int`, optional): minimum width the visualization at least covers. Defaults to 0.
            max_string_width (`int`, optional): maximum width the visualization never exceeds: None == +inf. Defaults to None.

        Returns:
            "str": visualization of the tree
        """
        
        PARENTHESES_OPEN : Final[str] = '['
        PARENTHESES_CLOSE: Final[str] = ']'
        PADDING          : Final[str] = '-'
        
        output: str = ""
        queue: list[Section_Person_Solver] = [section_to_visualize]
        
        # -------------------------------------- #
        # configure width and right shift offset #
        # -------------------------------------- #
        
        total_range  : Final[Dates_Delta] = section_to_visualize._determine_max_range()
        
        # if this limit still is to small for you then you definitely are going to have even bigger problems other than here
        max_string_width = max_string_width / total_range.days if max_string_width else 10e+69
        min_string_width = min_string_width / total_range.days if min_string_width else 0
        
        width_per_day: Final[float] = min( max( min_string_width, section_to_visualize._determine_min_width_per_range() ), max_string_width )
        
        DBG_PRINT( f"{width_per_day = }")
        DBG_PRINT( f"det width = {section_to_visualize._determine_min_width_per_range()}")
        DBG_PRINT( f"min width = {min_string_width}")
        DBG_PRINT( f"max width = {max_string_width}")
        
        # ------------------ #
        # visualization step #
        # ------------------ #
        while queue:
            cursor: date = total_range.date_low
            for i, section in enumerate(queue):
                # Layout:
                # [-----{p.name?}------]
                
                name = section.manages_person.name if section.manages_person else ""
                
                offset_space = max(0, (section.date_range.date_low - cursor).days * width_per_day)
                offset_space = round(offset_space) if offset_space > 1 else 0
                
                cursor += timedelta( days=offset_space/width_per_day )
                
                width_raw    = ( section.date_range.date_high - cursor ).days * width_per_day
                width_avail  = round(width_raw) - 2 # -2 parentheses at minimum
                
                output += ' '*offset_space + PARENTHESES_OPEN + name.center( width_avail, PADDING )[:width_avail] + PARENTHESES_CLOSE
                
                cursor += timedelta( days=round(width_raw)/width_per_day )
            
            output += '\n'
            
            queue = sorted(
                (sub
                for node in queue
                for sub in node.sub_nodes),
                key=lambda s: s.date_range.date_low,
            )
        
        # ------------------ #
        # handling time line #
        # ------------------ #
        if add_time_line:
            DATE_DAY_FORMAT  : Final[str] = "%d.%b.%y" # => const length = 2+1+3+1+2 = 9
            DATE_MONTH_FORMAT: Final[str] = "%b%y"     # => const length =     3  +2 = 5
            
            SIZE_SPACING     : Final[int] = 3
            
            SIZE_DAY_FORMAT  : Final[int] = 9
            SIZE_MONTH_FORMAT: Final[int] = 5

            SIZE_DAY_TOTAL   : Final[int] = SIZE_DAY_FORMAT   + SIZE_SPACING
            SIZE_MONTH_TOTAL : Final[int] = SIZE_MONTH_FORMAT + SIZE_SPACING
            
            width_per_month  : Final[float] = Dates_Delta.DAYS_IN_MONTH * width_per_day
            
            months_per_mark: Final[int] = ceil( SIZE_MONTH_TOTAL / width_per_month )
            days_per_mark  : Final[int] = ceil( SIZE_DAY_TOTAL   / width_per_day   )
            
            
            _, string_width = max_width_of_strings( output.splitlines() )
            
            months_in_string: Final[int] = floor( string_width / width_per_month )
            
            v_line    = " " * string_width
            date_line = " " * string_width
            
            size_total   : int
            format_string: str
            mark_callback: Callable[[int], date]
            
            # -------------------- #
            # strategy configuring #
            # -------------------- #
            if months_in_string >= 2:
                size_total    = SIZE_MONTH_TOTAL
                format_string = DATE_MONTH_FORMAT
                def mark_callback( i:int ) -> date:
                    year_overflow, month = divmod( total_range.date_low.month + i*months_per_mark - 1, 12 )
                    return date( total_range.date_low.year + year_overflow, month + 1, 1 )
            else:
                size_total    = SIZE_DAY_TOTAL
                format_string = DATE_DAY_FORMAT
                def mark_callback( i:int ) -> date:
                    return total_range.date_low + timedelta( i * days_per_mark )
            
            # ------------------ #
            # strategy execution #
            # ------------------ #
            date_line += " " * size_total
            for i in range( ceil( string_width / size_total ) ):
                mark: date = mark_callback( i )
                
                ddays = ( mark - total_range.date_low ).days
                
                if ddays < 0:
                    continue
                
                write_index = ceil( ddays * width_per_day )
                
                if write_index >= string_width-1:
                    break
                
                v_line    = replace_substring( v_line, write_index, '|' )
                date_line = replace_substring( date_line, write_index, mark.strftime( format_string ) )
            
            
            output += v_line + "\n" + date_line + "\n"
            
        
        return output

    
    def print_as_tree(self, *, _depth:int=0) -> None:
        """
        prints out the structure/hierarchy of a tree/node

        layout:
        >>> "date-range"\t"min-width-per-day"\t"person-name-if-not-None-else-'---'"
        >>> | "sub-tree-A"
        >>> |   | "sub-sub-tree"
        >>> |   | ...
        >>> | "sub-tree-B"
        >>> | ...
        """
        print( '|  '*_depth, self.date_range, '\t', f"{self._determine_min_width_per_range():8.5f}", '\t', self.manages_person.name if self.manages_person else "---", sep='', flush=True )
        for sub in self.sub_nodes:
            sub.print_as_tree( _depth=_depth+1 )
    
    #------------------------#
    #  local/private helper  #
    #------------------------#
    def _determine_min_width_per_range(self) -> float:
        """
        determines the minimum width per day required to "accurately" visualize this tree

        statistically filters out extremely large width values which are introduced by small (i.e. few days) date-ranges and larger person::name's
        
        Returns:
            `float`: minimum width in characters per day required to visualize this tree
        """
        
        # minimum layout:
        # [{name}] ==> width_avail >= 2 + len(name)
        
        
        # filter can be tuned via the `FILTER_MAGNITUDE_THRESHOLD` value.
        # This filters out each width-value 'w' whose ratio between the base variance and the variance w/o 'w' exceeds this threshold.
        FILTER_MAGNITUDE_THRESHOLD: Final[float] = 100.0
        
        
        if self.date_range.days <= 0:
            return 0
        
        len_name = len(self.manages_person.name) if self.manages_person else 0
        
        req_width: float = (2.0 + len_name) / self.date_range.days
        
        sub_widths = sorted( [req_width] + [ s._determine_min_width_per_range() for s in self.sub_nodes ] )
        
        if len(sub_widths) == 1:
            DBG_PRINT( "-", self.date_range, req_width, sub_widths, sep='\t', flush=True )
            return req_width
        
        DBG_PRINT( f"\nstarted filter => {sub_widths = }" )
        
        
        #------------------------------------------------#
        #  statistically filtering out excessive values  #
        #------------------------------------------------#
        
        base_mean, base_median, base_var = simple_statistics( sub_widths )
        old_base = base_mean + 1
        while old_base != base_mean:
            old_base = base_mean
            DBG_PRINT( f"\n=> {sub_widths = }" )
            DBG_PRINT( f"=> {base_mean = }\t{base_median = }\t{base_var = }" )
            
            exclusion_indices: list[int] = []
            for i in range(len(sub_widths)):
                new_mean, new_median, new_var = simple_statistics( sub_widths[:i] + sub_widths[i+1:] )

                mag = 0
                if new_var != 0 and (mag:=base_var / new_var) > FILTER_MAGNITUDE_THRESHOLD:
                    exclusion_indices.append( i )
                    
                    base_mean, base_median, base_var = new_mean, new_median, new_var

                DBG_PRINT(
                    f"mean:   {new_mean}",
                    f"median: {new_median}",
                    f"var:    {new_var}",
                    f"mag:    {mag or 0}",
                    f"{exclusion_indices = }",
                    "-"*20,
                    sep='\n'
                )
            
            sub_widths = [ x for i, x in enumerate(sub_widths) if i not in exclusion_indices ]
        DBG_PRINT( f"finished filter => {sub_widths = }\n" )
        
        return max( sub_widths or [req_width] )
    
    def _determine_max_range(self) -> Dates_Delta:
        """
        determine the total range of dates this tree covers

        Returns:
            `Dates_Delta`: total range this tree and its subtrees covers
        """
        ranges: list[Dates_Delta] = [self.date_range] + [ s._determine_max_range() for s in self.sub_nodes ]
        
        d_min = min( map( lambda r: r.date_low, ranges ) )
        d_max = max( map( lambda r: r.date_high, ranges ) )
        
        return Dates_Delta( d_min, d_max )
    

db_callback_t: TypeAlias = Callable[[date, date], tuple[list[db.Reading], list[db.Person]]]
invoice_t = NamedTuple("invoice_t", [("person", db.Person), ("payment", float)] )
class Invoice:
    """
    Create a payment invoice for a given date range and payment value

    This invoice class will calculate the correct distribution of the total payment for 
    all persons with occupancy in the given date range
    """
    __date_start: date
    __date_end  : date
    __costs     : float
    
    __solver_tree: Section_Person_Solver
    
    def __init__(self, date_start: date, date_end: date, payment: float ):
        assert date_start < date_end, "the supplied date end must be larger(later) then the supplied start date"
        
        self.__date_start = date_start
        self.__date_end   = date_end
        self.__costs      = payment
        
        self.__solver_tree = None
    
    def get_invoice(
        self,
        exclude_names:list[str]     = None,
        db_callback  :db_callback_t = db.get_data_between,
        normalize_distribution:bool = True
        ) -> list[invoice_t]:
        """
        ### Generate the invoice
        This method generates the distribution of the total payment for each person with occupancy in the given database

        ---
        #### The underlying algorithm can be summarized as depicted by the following examples:
        
        A layout structured like this:
        ```
        [-------Invoice-Range------]
        [---------Person-A---------]
        [--Person-B--][--Person-C--]
        ```
        
        where:
            - `Person-A` is present in the complete `Invoice-Range`
            - `Person-B` and `Person-C` each for half of the `Invoice-Range`, whilst 'sharing' the costs with `Person-A`
        
        would result in the following distribution of the total costs:
            - `Person-A` = `50%`
            - `Person-B` = `25%`
            - `Person-C` = `25%`
        
        
        If now `Person-B` would be excluded (or generally that slot being unoccupied)
        the layout would look like this:
        ```
        [-------Invoice-Range------]
        [---------Person-A---------]
        [------------][--Person-C--]
        ```
        where:
            - `Person-A` is present in the complete `Invoice-Range`
            - `Person-C` is present for half of the `Invoice-Range`, whilst 'sharing' the costs with `Person-A`
        
        this layout would then be internally transformed to the following layout:
        ```
        [-------Invoice-Range------]
        [---------Person-A---------]
        [--Person-A--][--Person-C--]
        ```
        
        there then the resulting distribution of the total costs would be determined as:
            - `Person-A` = `75%`
            - `Person-C` = `25%`
        

        In the special case there the layout would look something like this:
        ```
        [-------Invoice-Range------]
              [------Person-A------]
                      [--Person-C--]
        ```
        where:
            - `Person-A` is `x%` present in the `Invoice-Range`
            - `Person-C` is `y%` present in the Range of `Person-A`, whilst 'sharing' the costs with `Person-A`
        
        the resulting distribution depends on the `normalize_distribution` flag:
        
        If set to `False` would result in the distribution:
            - `Person-A` = `x% * (100% - y% / 2)`
            - `Person-C` = `x% * y% / 2`
            - => where `Person-A + Person-C` = `x% != 100%`
        
        If set to `True` would result in the distribution:
            - `Person-A` = `x% * (100% - y% / 2) / (x% * (100% - y% / 2) + x% * y% / 2` = `100% - y% / 2`
            - `Person-C` = `(x% * y% / 2) / (x% * (100% - y% / 2) + x% * y% / 2)` = `%y / 2`
            - => where `Person-A + Person-C` = `100% - y% / 2 + %y / 2 = 100%`

        ---
        #### Excluding persons
        
        a set of persons (identified by their `.name` attribute) can be excluded from the invoice
        with their associate payments being correctly distributed amongst the overlying persons.
        See the examples above for more information
        

        Args:
            exclude_names (`list[str]`, optional): names of persons to exclude from the distribution. Defaults to None.
            db_callback (`db_callback_t`, optional): database callback to get persons in between a date-range. Defaults to db.get_data_between.
            normalize_distribution (`bool`, optional): if set to True will assure that the calculated distribution adds up to 100% and will adjust each distribution to satisfy this criteria, otherwise will simply return the calculated distribution

        Returns:
            `list[invoice_t]`: invoice tuples of the calculated distribution costs sorted by person::name
        """
        
        _, persons = db_callback( self.__date_start, self.__date_end )
        
        accountable_persons: list[db.Person] = [
            db.Person( p.name, p.move_in, p.move_out if p.move_out else date.today() )
            for p
            in persons
            if p.move_in and ( (not p.name in exclude_names) if exclude_names else True )
        ]
        
        if not accountable_persons:
            return []
        
        self.__solver_tree = Section_Person_Solver( Dates_Delta( self.__date_start, self.__date_end ) ) \
                             .solve( accountable_persons )                                              \
                             .simplify()

        self.__solver_tree.assert_valid_solver_tree_structure()
        
        contributions = self.__solver_tree.calculate_contributions()
        
        # => normalize the contribution vector to compensate for open payments and floating point rounding errors
        if normalize_distribution:
            contributions = contributions.normalize()
        
        contributions *= self.__costs
        
        return sorted( (invoice_t(p, c) for p, c in contributions), key=lambda inv: inv.person.name )
    
    
    def get_visualization(self, min_string_width:int=0, max_string_width:int=None) -> str:
        """
        ### visualize a Section tree as a bar like graph

        ---
        #### Layout
        a tree of the pseudo structure
        >>> DD(A, E)        Person_A
        >>> |  DD(C, F)     Person_B
        >>> |  DD(A, D)     Person_C
        >>> |  |  DD(B, D)  Person_D
        
        would be visualized with a time line like this:
        >>> [-------------------Person_A-------------------]             
        >>>                         [-------------Person_B-------------] 
        >>> [-------------Person_C-------------]                         
        >>>             [-------Person_D-------]                         
        >>> |           |           |           |           |           |
        >>> A           B           C           D           E           F
        

        Args:
            section_to_visualize (`Section_Person_Solver`): tree to visualize
            add_time_line (`bool`, optional): iff True appends a correctly scaled and placed time line at the bottom of the visualization. Defaults to False.
            min_string_width (`int`, optional): minimum width the visualization at least covers. Defaults to 0.
            max_string_width (`int`, optional): maximum width the visualization never exceeds: None == +inf. Defaults to None.

        Returns:
            `str`: visualization of the tree
        """
        assert self.__solver_tree, ".get_invoice(...) must be called beforehand calling this .get_visualization() method"
        return Section_Person_Solver.visualize( self.__solver_tree, True, min_string_width, max_string_width )
    
    def _get_solver_tree(self) -> Section_Person_Solver:
        return self.__solver_tree


if __name__ == "__main__":
    s0  = Section_Person_Solver( Dates_Delta(date(2024, 2, 1), date(2024, 12, 31)) )
    s01 = Section_Person_Solver( Dates_Delta(date(2024, 1, 1), date(2024, 5,   1))  , db.Person( "Marie" ) )
    s11 = Section_Person_Solver( Dates_Delta(date(2024, 1, 1), date(2024, 2,   1))  , db.Person( "Herbert" ) )
    s12 = Section_Person_Solver( Dates_Delta(date(2024, 2, 1), date(2024, 6,   1))  , db.Person( "Adi" ) )
    s02 = Section_Person_Solver( Dates_Delta(date(2024, 5, 1), date(2025, 2,   1))  , db.Person( "Peter" ) )
    
    s0.sub_nodes  = [ s01, s02 ]
    s01.sub_nodes = [ s11, s12 ]
    
    ss0  = Section_Person_Solver( Dates_Delta(date(2024, 2, 21), date(2024, 3, 11)) )
    ss01 = Section_Person_Solver( Dates_Delta(date(2024, 2, 15), date(2024, 3,  1))  , db.Person( "Marie" ) )
    ss11 = Section_Person_Solver( Dates_Delta(date(2024, 2, 15), date(2024, 2, 19))  , db.Person( "Herbert" ) )
    ss12 = Section_Person_Solver( Dates_Delta(date(2024, 2, 19), date(2024, 3,  1))  , db.Person( "Adi" ) )
    ss02 = Section_Person_Solver( Dates_Delta(date(2024, 3,  1), date(2024, 3, 15))  , db.Person( "Peter" ) )
    
    ss0.sub_nodes  = [ ss01, ss02 ]
    ss01.sub_nodes = [ ss11, ss12 ]
    
    # print( Section_Person_Solver.visualize( s0 , True, 100 ), flush=True )
    # print( Section_Person_Solver.visualize( ss0, True, 100 ), flush=True )
    # print( "\n"*3, flush=True )
    
    
    # ---------------------------------------------------------------------------------------------

    INV_START = date( 2023,  2,  1 )
    INV_END   = date( 2023, 12, 31 )
    
    db_callback: db_callback_t = lambda dlow, dhigh: [[], [ 
                                                            db.Person("Person C", date(2023, 5,  6), None),
                                                            db.Person("Person B", date(2023, 2,  1), date(2023, 5,2)),
                                                            db.Person("Person A", date(2023, 2,  1), None), 
                                                            db.Person("Person D", date(2023, 3, 18), date(2023, 9, 2))
                                                            ]]
    
    inv_A = Invoice( INV_START, INV_END, 100.0 )
    pays_A = inv_A.get_invoice( None, db_callback )
    
    inv_B = Invoice( INV_START, INV_END, 100.0 )
    pays_B = inv_B.get_invoice( ["Person B", "Person D"], db_callback )
    
    
    payA_Person_A = pays_A[0].payment
    payA_Person_B = pays_A[1].payment
    payA_Person_C = pays_A[2].payment
    payA_Person_D = pays_A[3].payment
    payA_sum      = payA_Person_A + payA_Person_B + payA_Person_C + payA_Person_D
    
    
    payB_Person_A = pays_B[0].payment
    payB_Person_C = pays_B[1].payment
    payB_sum      = payB_Person_A + payB_Person_C

    
    #-------------------#
    #  Test validation  #
    #-------------------#
    def validate_em_all( *cond_err: tuple[bool, str] ) -> list[str]:
        return [ msg for cond, msg in cond_err if not cond ]
    
    def printout_validation( *cond_err: tuple[bool, str], width:int=80 ) -> None:
        err_msgs = validate_em_all( *cond_err )
        if err_msgs:
            print( "~*"*(width//2) )
            print( "TESTS FAILED:".center(width) )
            print( *[ m.center(width) for m in err_msgs ], sep="\n" )
            print( "~*"*(width//2) )
        else:
            print( "="*width )
            print( "ALL TESTS SUCCESSFUL".center(width) )
            print( "="*width )
    
    
    print( "\n", flush=True )
    print( f"=== Payments A ===" )
    inv_A._get_solver_tree().print_as_tree()
    print( inv_A.get_visualization(100, 200), flush=True )
    print( f"Person A: {payA_Person_A:>7.3f} %" )
    print( f"Person B: {payA_Person_B:>7.3f} %" )
    print( f"Person C: {payA_Person_C:>7.3f} %" )
    print( f"Person D: {payA_Person_D:>7.3f} %" )
    print( f"sum:      {payA_sum:7.3f} %" )
    
    
    printout_validation( 
        (round( payA_Person_A, 3 ) ==  50.300, f"payment for Person A must be  50.300 % but actually is {payA_Person_A:7.3f} %"), 
        (round( payA_Person_B, 3 ) ==   9.985, f"payment for Person B must be   9.985 % but actually is {payA_Person_B:7.3f} %"), 
        (round( payA_Person_C, 3 ) ==  26.952, f"payment for Person C must be  26.952 % but actually is {payA_Person_C:7.3f} %"), 
        (round( payA_Person_D, 3 ) ==  12.763, f"payment for Person D must be  12.763 % but actually is {payA_Person_D:7.3f} %"), 
        (round( payA_sum     , 3 ) == 100.000, f"sum of all payments  must be 100.000 % but actually is {payA_sum:7.3f} %"), 
    )
    
    print( "\n", flush=True )
    print( f"=== Payments B ===" )
    inv_B._get_solver_tree().print_as_tree()
    
    print( inv_B.get_visualization(100, 200), flush=True )
    print( f"Person_A: {payB_Person_A:>7.3f} %" )
    print( f"Person_C: {payB_Person_C:>7.3f} %" )
    print( f"sum:      {payB_sum:7.3f} %" )
    
    printout_validation( 
        (round( payB_Person_A, 3 ) ==  64.114, f"payment for Person A must be  64.114 % but actually is {round(payA_Person_A, 3):7.3f} %"), 
        (round( payB_Person_C, 3 ) ==  35.886, f"payment for Person C must be  35.886 % but actually is {round(payA_Person_C, 3):7.3f} %"), 
        (round( payB_sum     , 3 ) == 100.000, f"sum of all payments  must be 100.000 % but actually is {payA_sum:7.3f} %"), 
    )