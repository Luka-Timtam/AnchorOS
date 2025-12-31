import os
import logging
from supabase import create_client, Client
from datetime import datetime, date
import json
import timezone as tz

logger = logging.getLogger(__name__)


def _clear_cache():
    from cache import clear_all_cache
    clear_all_cache()

_supabase_client: Client = None
_client_initialized: bool = False

def get_supabase() -> Client:
    """
    Returns the singleton Supabase client instance.
    The client is created exactly once per application lifecycle.
    Subsequent calls return the cached instance without any re-initialization.
    """
    global _supabase_client, _client_initialized
    
    if _supabase_client is not None:
        return _supabase_client
    
    if _client_initialized:
        raise RuntimeError("Supabase client was previously initialized but is now None. This should not happen.")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise RuntimeError(
            "Supabase credentials missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
        )
    
    logger.info("[Supabase] Creating client instance (this should happen once per app lifecycle)")
    
    _supabase_client = create_client(url, key)
    _client_initialized = True
    
    logger.info("[Supabase] Client instance created successfully")
    
    return _supabase_client


def check_connection():
    """
    Verifies database connectivity with a minimal query.
    Uses the singleton client - does not create a new connection.
    """
    try:
        client = get_supabase()
        result = client.table("user_stats").select("id").limit(1).execute()
        logger.info("[Supabase] Connection verified successfully")
        return True
    except Exception as e:
        logger.error(f"[Supabase] Connection error: {e}")
        return False


def is_client_initialized() -> bool:
    """Returns True if the Supabase client has been initialized."""
    return _client_initialized


def serialize_value(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def serialize_row(row: dict) -> dict:
    return {k: serialize_value(v) for k, v in row.items()}


def parse_datetime(value):
    return tz.parse_datetime_to_local(value)


def parse_date(value):
    return tz.parse_date_only(value)


class SupabaseModel:
    __tablename__ = None
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def _parse_row(cls, row: dict):
        if row is None:
            return None
        obj = cls(**row)
        return obj
    
    @classmethod
    def query_all(cls, order_by=None, order_desc=False, limit=None):
        client = get_supabase()
        query = client.table(cls.__tablename__).select("*")
        if order_by:
            query = query.order(order_by, desc=order_desc)
        if limit:
            query = query.limit(limit)
        result = query.execute()
        return [cls._parse_row(row) for row in result.data]
    
    @classmethod
    def query_filter(cls, filters: dict, order_by=None, order_desc=False, limit=None):
        client = get_supabase()
        query = client.table(cls.__tablename__).select("*")
        for key, value in filters.items():
            query = query.eq(key, serialize_value(value))
        if order_by:
            query = query.order(order_by, desc=order_desc)
        if limit:
            query = query.limit(limit)
        result = query.execute()
        return [cls._parse_row(row) for row in result.data]
    
    @classmethod
    def get_by_id(cls, id):
        client = get_supabase()
        result = client.table(cls.__tablename__).select("*").eq("id", id).limit(1).execute()
        if result.data:
            return cls._parse_row(result.data[0])
        return None
    
    @classmethod
    def get_first(cls, filters: dict = None):
        client = get_supabase()
        query = client.table(cls.__tablename__).select("*")
        if filters:
            for key, value in filters.items():
                query = query.eq(key, serialize_value(value))
        result = query.limit(1).execute()
        if result.data:
            return cls._parse_row(result.data[0])
        return None
    
    @classmethod
    def count(cls, filters: dict = None):
        client = get_supabase()
        query = client.table(cls.__tablename__).select("id", count="exact")
        if filters:
            for key, value in filters.items():
                query = query.eq(key, serialize_value(value))
        result = query.execute()
        return result.count if result.count is not None else len(result.data)
    
    @classmethod
    def insert(cls, data: dict):
        client = get_supabase()
        serialized = serialize_row(data)
        result = client.table(cls.__tablename__).insert(serialized).execute()
        if result.data:
            _clear_cache()
            return cls._parse_row(result.data[0])
        return None
    
    @classmethod
    def update_by_id(cls, id, data: dict):
        client = get_supabase()
        serialized = serialize_row(data)
        result = client.table(cls.__tablename__).update(serialized).eq("id", id).execute()
        if result.data:
            _clear_cache()
            return cls._parse_row(result.data[0])
        return None
    
    @classmethod
    def delete_by_id(cls, id):
        client = get_supabase()
        client.table(cls.__tablename__).delete().eq("id", id).execute()
        _clear_cache()
    
    def save(self):
        client = get_supabase()
        data = {k: serialize_value(v) for k, v in self.__dict__.items() if not k.startswith('_')}
        
        if hasattr(self, 'id') and self.id:
            result = client.table(self.__tablename__).update(data).eq("id", self.id).execute()
        else:
            if 'id' in data:
                del data['id']
            result = client.table(self.__tablename__).insert(data).execute()
        
        if result.data:
            _clear_cache()
            for key, value in result.data[0].items():
                setattr(self, key, value)
        return self
    
    def delete(self):
        if hasattr(self, 'id') and self.id:
            client = get_supabase()
            client.table(self.__tablename__).delete().eq("id", self.id).execute()
            _clear_cache()


class Lead(SupabaseModel):
    __tablename__ = 'leads'
    
    @staticmethod
    def status_choices():
        return ['new', 'contacted', 'call_booked', 'follow_up', 'proposal_sent', 'closed_won', 'closed_lost']
    
    @staticmethod
    def website_quality_choices():
        return ['no_website', 'outdated', 'poor_design', 'not_mobile_friendly', 'slow_loading', 'broken_features']
    
    @staticmethod
    def win_reason_choices():
        return [
            'Good fit for product',
            'Pricing match',
            'Pre-built demo impressed them',
            'Fast response time',
            'Strong rapport / relationship',
            'Referral',
            'Previous positive interaction'
        ]
    
    @staticmethod
    def loss_reason_choices():
        return [
            'Pricing too high',
            'Timing not right',
            'Already working with someone',
            'No response / ghosted',
            'Low priority for client',
            'Not a good fit',
            'Chosen competitor'
        ]
    
    def get_close_reasons_list(self):
        if not hasattr(self, 'close_reason') or not self.close_reason:
            return []
        return [r.strip() for r in self.close_reason.split(',') if r.strip()]
    
    @classmethod
    def _parse_row(cls, row: dict):
        if row is None:
            return None
        obj = cls(**row)
        # Parse datetime fields
        datetime_fields = ['created_at', 'updated_at', 'converted_at', 'archived_at', 'closed_at', 'last_contacted_at']
        for field in datetime_fields:
            if hasattr(obj, field) and getattr(obj, field):
                setattr(obj, field, parse_datetime(getattr(obj, field)))
        # Parse date fields
        date_fields = ['next_action_date']
        for field in date_fields:
            if hasattr(obj, field) and getattr(obj, field):
                value = getattr(obj, field)
                if isinstance(value, str):
                    setattr(obj, field, parse_date(value))
        return obj


class Client(SupabaseModel):
    __tablename__ = 'clients'
    
    @staticmethod
    def project_type_choices():
        return ['website', 'hosting_only', 'saas_only', 'bundle']
    
    @staticmethod
    def status_choices():
        return ['active', 'completed', 'paused', 'cancelled']
    
    @classmethod
    def _parse_row(cls, row: dict):
        if row is None:
            return None
        obj = cls(**row)
        # Parse datetime fields
        datetime_fields = ['created_at', 'updated_at']
        for field in datetime_fields:
            if hasattr(obj, field) and getattr(obj, field):
                setattr(obj, field, parse_datetime(getattr(obj, field)))
        # Parse date fields
        date_fields = ['start_date']
        for field in date_fields:
            if hasattr(obj, field) and getattr(obj, field):
                value = getattr(obj, field)
                if isinstance(value, str):
                    setattr(obj, field, parse_date(value))
        return obj


class OutreachLog(SupabaseModel):
    __tablename__ = 'outreach_logs'
    
    @staticmethod
    def type_choices():
        return ['email', 'call', 'dm', 'in_person', 'other']
    
    @staticmethod
    def outcome_choices():
        return ['contacted', 'booked_call', 'no_response', 'closed_won', 'closed_lost', 'follow_up_set']
    
    @classmethod
    def _parse_row(cls, row: dict):
        if row is None:
            return None
        obj = cls(**row)
        # Parse datetime/date fields
        if hasattr(obj, 'date') and getattr(obj, 'date'):
            value = getattr(obj, 'date')
            if isinstance(value, str):
                setattr(obj, 'date', parse_date(value))
        return obj


class Task(SupabaseModel):
    __tablename__ = 'tasks'
    
    @staticmethod
    def status_choices():
        return ['open', 'in_progress', 'done']
    
    @classmethod
    def _parse_row(cls, row: dict):
        if row is None:
            return None
        obj = cls(**row)
        # Parse datetime/date fields
        if hasattr(obj, 'due_date') and getattr(obj, 'due_date'):
            value = getattr(obj, 'due_date')
            if isinstance(value, str):
                setattr(obj, 'due_date', parse_date(value))
        if hasattr(obj, 'created_at') and getattr(obj, 'created_at'):
            setattr(obj, 'created_at', parse_datetime(getattr(obj, 'created_at')))
        return obj


class UserSettings(SupabaseModel):
    __tablename__ = 'user_settings'
    
    DEFAULT_WIDGET_ORDER = [
        'followups',
        'gamification_stats',
        'daily_mission',
        'boss_battle',
        'focus_session',
        'activity_calendar',
        'lead_stats',
        'outreach_stats',
        'mrr_forecast',
        'leads_by_status',
        'outreach_deals_charts',
        'revenue_chart'
    ]
    
    DEFAULT_WIDGET_NAMES = {
        'followups': 'Follow-Up Reminders',
        'gamification_stats': 'XP & Streak Progress',
        'daily_mission': 'Daily Mission Challenge',
        'boss_battle': 'Monthly Boss Battle',
        'focus_session': 'Focus Timer',
        'activity_calendar': 'Activity Feed & Calendar',
        'lead_stats': 'New Leads & Clients',
        'outreach_stats': 'Outreach Activity',
        'mrr_forecast': 'MRR & Revenue Forecast',
        'leads_by_status': 'Lead Pipeline Status',
        'outreach_deals_charts': 'Weekly Charts',
        'revenue_chart': 'Revenue Trend Graph'
    }
    
    def get_dashboard_order(self):
        if hasattr(self, 'dashboard_order') and self.dashboard_order:
            try:
                order = json.loads(self.dashboard_order) if isinstance(self.dashboard_order, str) else self.dashboard_order
                for w in self.DEFAULT_WIDGET_ORDER:
                    if w not in order:
                        order.append(w)
                return order
            except:
                pass
        return self.DEFAULT_WIDGET_ORDER.copy()
    
    def set_dashboard_order(self, order):
        self.dashboard_order = json.dumps(order)
    
    def get_dashboard_active(self):
        if hasattr(self, 'dashboard_active') and self.dashboard_active:
            try:
                active = json.loads(self.dashboard_active) if isinstance(self.dashboard_active, str) else self.dashboard_active
                for w in self.DEFAULT_WIDGET_ORDER:
                    if w not in active:
                        active[w] = True
                return active
            except:
                pass
        return {w: True for w in self.DEFAULT_WIDGET_ORDER}
    
    def set_dashboard_active(self, active):
        self.dashboard_active = json.dumps(active)
    
    def is_widget_active(self, widget_id):
        return self.get_dashboard_active().get(widget_id, True)
    
    @staticmethod
    def get_settings():
        settings = UserSettings.get_first()
        if not settings:
            settings = UserSettings.insert({})
        return settings
    
    def check_pause_expiry(self):
        if hasattr(self, 'pause_active') and self.pause_active and hasattr(self, 'pause_end') and self.pause_end:
            pause_end = parse_date(self.pause_end)
            if pause_end and date.today() > pause_end:
                self.pause_active = False
                self.pause_start = None
                self.pause_end = None
                self.pause_reason = None
                self.save()
                
                stats = UserStats.get_stats()
                if stats and hasattr(stats, 'last_outreach_date') and stats.last_outreach_date:
                    last_date = parse_date(stats.last_outreach_date)
                    if last_date and last_date < pause_end:
                        stats.last_outreach_date = pause_end
                        stats.save()
                return True
        return False
    
    def is_paused(self):
        self.check_pause_expiry()
        return getattr(self, 'pause_active', False)
    
    def remaining_pause_days(self):
        if hasattr(self, 'pause_active') and self.pause_active and hasattr(self, 'pause_end') and self.pause_end:
            pause_end = parse_date(self.pause_end)
            if pause_end:
                delta = (pause_end - date.today()).days
                return max(0, delta)
        return 0


class UserStats(SupabaseModel):
    __tablename__ = 'user_stats'
    
    LEVELS = [
        (1, 0),
        (2, 150),
        (3, 400),
        (4, 800),
        (5, 1400),
        (6, 2200),
        (7, 3200),
        (8, 4500),
        (9, 6500),
        (10, 9000),
        (11, 12000),
        (12, 16000),
        (13, 20000),
        (14, 25000),
        (15, 30000),
    ]
    
    @staticmethod
    def get_stats():
        stats = UserStats.get_first()
        if not stats:
            stats = UserStats.insert({
                'current_xp': 0,
                'current_level': 1,
                'current_outreach_streak_days': 0,
                'longest_outreach_streak_days': 0
            })
        return stats
    
    def get_level_from_xp(self):
        xp = getattr(self, 'current_xp', 0) or 0
        level = 1
        for lvl, threshold in self.LEVELS:
            if xp >= threshold:
                level = lvl
            else:
                break
        return level
    
    def xp_for_next_level(self):
        current = self.get_level_from_xp()
        for lvl, threshold in self.LEVELS:
            if lvl == current + 1:
                return threshold
        return None
    
    def xp_for_current_level(self):
        current = self.get_level_from_xp()
        for lvl, threshold in self.LEVELS:
            if lvl == current:
                return threshold
        return 0


class Achievement(SupabaseModel):
    __tablename__ = 'achievements'
    
    @staticmethod
    def seed_defaults():
        defaults = [
            {'key': 'streak_7', 'name': 'Week Warrior', 'description': 'Maintain a 7-day outreach streak'},
            {'key': 'streak_30', 'name': 'Consistency King', 'description': 'Maintain a 30-day outreach streak'},
            {'key': 'xp_1000', 'name': 'Rising Star', 'description': 'Earn 1,000 XP'},
            {'key': 'xp_5000', 'name': 'Power Player', 'description': 'Earn 5,000 XP'},
            {'key': 'outreach_100', 'name': 'Outreach Machine', 'description': 'Log 100 outreach activities'},
            {'key': 'deals_10', 'name': 'Deal Closer', 'description': 'Close 10 deals'},
        ]
        for item in defaults:
            existing = Achievement.get_first({'key': item['key']})
            if not existing:
                Achievement.insert(item)


class Goal(SupabaseModel):
    __tablename__ = 'goals'
    
    @staticmethod
    def goal_types():
        return ['daily_outreach', 'weekly_outreach', 'monthly_revenue', 'monthly_deals']
    
    @staticmethod
    def get_or_create(goal_type, period):
        goal = Goal.get_first({'goal_type': goal_type, 'period': period})
        if not goal:
            goal = Goal.insert({
                'goal_type': goal_type,
                'period': period,
                'target_value': 0,
                'is_manual': False
            })
        return goal


class XPLog(SupabaseModel):
    __tablename__ = 'xp_logs'


class OutreachTemplate(SupabaseModel):
    __tablename__ = 'outreach_templates'
    
    @staticmethod
    def category_choices():
        return ['email', 'dm', 'call']
    
    @staticmethod
    def subcategory_choices():
        return ['cold_outreach', 'follow_up', 'cold_call_script', 'objection_handling', 'booking_confirmation', 'proposal', 'other']


class LevelReward(SupabaseModel):
    __tablename__ = 'level_rewards'
    
    @staticmethod
    def seed_defaults():
        defaults = [
            {'level_interval': 2, 'reward_text': 'Bag of favourite lollies'},
            {'level_interval': 5, 'reward_text': 'Small treat of your choice'},
            {'level_interval': 10, 'reward_text': 'Full free day or special reward'},
        ]
        for item in defaults:
            existing = LevelReward.get_first({'level_interval': item['level_interval']})
            if not existing:
                LevelReward.insert({**item, 'is_active': True})


class MilestoneReward(SupabaseModel):
    __tablename__ = 'milestone_rewards'
    
    @staticmethod
    def seed_defaults():
        defaults = [
            {'target_level': 10, 'reward_text': 'Take yourself out for sushi'},
            {'target_level': 25, 'reward_text': 'Buy a small gift for yourself'},
            {'target_level': 50, 'reward_text': 'Weekend getaway fund contribution'},
        ]
        for item in defaults:
            existing = MilestoneReward.get_first({'target_level': item['target_level']})
            if not existing:
                MilestoneReward.insert({**item, 'is_active': True})


class UnlockedReward(SupabaseModel):
    __tablename__ = 'unlocked_rewards'


class RevenueReward(SupabaseModel):
    __tablename__ = 'revenue_rewards'
    
    @staticmethod
    def seed_defaults():
        defaults = [
            {'target_revenue': 1000, 'reward_text': 'Nice dinner out', 'reward_icon': 'utensils'},
            {'target_revenue': 2500, 'reward_text': 'New pair of sneakers', 'reward_icon': 'shoe'},
            {'target_revenue': 5000, 'reward_text': 'Weekend spa day', 'reward_icon': 'spa'},
            {'target_revenue': 10000, 'reward_text': 'New tech gadget', 'reward_icon': 'laptop'},
            {'target_revenue': 15000, 'reward_text': 'Designer item', 'reward_icon': 'star'},
            {'target_revenue': 25000, 'reward_text': 'Weekend getaway trip', 'reward_icon': 'plane'},
            {'target_revenue': 50000, 'reward_text': 'Luxury watch', 'reward_icon': 'watch'},
            {'target_revenue': 75000, 'reward_text': 'High-end home upgrade', 'reward_icon': 'home'},
            {'target_revenue': 100000, 'reward_text': 'Dream vacation package', 'reward_icon': 'globe'},
            {'target_revenue': 150000, 'reward_text': 'Investment portfolio contribution', 'reward_icon': 'chart'},
            {'target_revenue': 200000, 'reward_text': 'Luxury experience of choice', 'reward_icon': 'crown'},
            {'target_revenue': 250000, 'reward_text': 'Major life upgrade fund', 'reward_icon': 'rocket'},
            {'target_revenue': 300000, 'reward_text': 'McLaren MP4-12C Spider', 'reward_icon': 'car'},
        ]
        for item in defaults:
            existing = RevenueReward.get_first({'target_revenue': item['target_revenue']})
            if not existing:
                RevenueReward.insert({**item, 'is_active': True})


class UserTokens(SupabaseModel):
    __tablename__ = 'user_tokens'
    
    @staticmethod
    def get_tokens():
        tokens = UserTokens.get_first()
        if not tokens:
            tokens = UserTokens.insert({'total_tokens': 0})
        return tokens
    
    @staticmethod
    def get_balance():
        tokens = UserTokens.get_tokens()
        return getattr(tokens, 'total_tokens', 0) or 0
    
    @staticmethod
    def add_tokens(amount, reason):
        tokens = UserTokens.get_tokens()
        new_total = (getattr(tokens, 'total_tokens', 0) or 0) + amount
        tokens.total_tokens = new_total
        tokens.save()
        TokenTransaction.insert({'amount': amount, 'reason': reason})
        return new_total
    
    @staticmethod
    def spend_tokens(amount, reason):
        tokens = UserTokens.get_tokens()
        current = getattr(tokens, 'total_tokens', 0) or 0
        if current >= amount:
            tokens.total_tokens = current - amount
            tokens.save()
            TokenTransaction.insert({'amount': -amount, 'reason': reason})
            return True
        return False


class TokenTransaction(SupabaseModel):
    __tablename__ = 'token_transactions'


class RewardItem(SupabaseModel):
    __tablename__ = 'reward_items'
    
    @staticmethod
    def seed_defaults():
        defaults = [
            {'name': 'Bag of favourite lollies', 'cost': 8, 'description': 'Treat yourself to your favourite sweets'},
            {'name': 'Coffee or drink', 'cost': 10, 'description': 'A nice coffee or beverage of your choice'},
            {'name': '1 hour guilt-free gaming', 'cost': 12, 'description': 'Take a break and play your favourite game'},
            {'name': 'Nice lunch treat', 'cost': 20, 'description': 'Enjoy a nice lunch out'},
            {'name': 'Car care item', 'cost': 50, 'description': 'Something nice for your car'},
            {'name': 'T-shirt', 'cost': 75, 'description': 'Buy yourself a new t-shirt'},
        ]
        for item in defaults:
            existing = RewardItem.get_first({'name': item['name']})
            if not existing:
                RewardItem.insert({**item, 'is_active': True})


class DailyMission(SupabaseModel):
    __tablename__ = 'daily_missions'
    
    @staticmethod
    def is_weekday(check_date=None):
        """Check if a date is a weekday (Monday=0 through Friday=4)"""
        if check_date is None:
            check_date = date.today()
        return check_date.weekday() < 5
    
    @staticmethod
    def get_today_mission():
        today = date.today()
        # No missions on weekends
        if not DailyMission.is_weekday(today):
            return None
        mission = DailyMission.get_first({'mission_date': today.isoformat()})
        return mission
    
    @staticmethod
    def create_today_mission():
        import random
        today = date.today()
        
        # Don't create missions on weekends
        if not DailyMission.is_weekday(today):
            return None
        
        today_str = today.isoformat()
        existing = DailyMission.get_first({'mission_date': today_str})
        if existing:
            return existing
        
        mission_types = [
            {'type': 'outreach', 'target': random.randint(3, 5), 'tokens': 5, 'description': 'Complete outreach activities today'},
            {'type': 'tasks', 'target': random.randint(2, 4), 'tokens': 4, 'description': 'Complete tasks from your task list'},
            {'type': 'follow_ups', 'target': random.randint(1, 3), 'tokens': 3, 'description': 'Follow up with leads'},
        ]
        selected = random.choice(mission_types)
        
        return DailyMission.insert({
            'mission_date': today_str,
            'mission_type': selected['type'],
            'description': selected['description'],
            'target_count': selected['target'],
            'reward_tokens': selected['tokens'],
            'is_completed': False
        })


class BossBattle(SupabaseModel):
    __tablename__ = 'boss_fights'
    
    @staticmethod
    def get_current_month():
        return date.today().strftime('%Y-%m')
    
    @staticmethod
    def get_current_battle():
        current_month = BossBattle.get_current_month()
        battle = BossBattle.get_first({'month': current_month})
        return battle
    
    @staticmethod
    def create_current_battle():
        current_month = BossBattle.get_current_month()
        
        existing = BossBattle.get_first({'month': current_month})
        if existing:
            return existing
        
        import random
        
        boss_types = [
            {'type': 'outreach', 'desc': 'Complete outreach activities', 'target': random.randint(40, 60)},
            {'type': 'revive_leads', 'desc': 'Revive cold leads', 'target': random.randint(5, 10)},
        ]
        selected = random.choice(boss_types)
        
        return BossBattle.insert({
            'month': current_month,
            'description': f"Monthly Challenge: {selected['desc']}",
            'boss_type': selected['type'],
            'target_value': selected['target'],
            'progress_value': 0,
            'reward_tokens': 50,
            'is_completed': False
        })


class ActivityLog(SupabaseModel):
    __tablename__ = 'activity_log'
    
    @classmethod
    def _parse_row(cls, row: dict):
        if row is None:
            return None
        obj = cls(**row)
        if hasattr(obj, 'timestamp') and obj.timestamp:
            obj.timestamp = parse_datetime(obj.timestamp)
        return obj
    
    def get_icon(self):
        icons = {
            'outreach_logged': 'envelope',
            'lead_contacted': 'user-plus',
            'call_booked': 'phone',
            'proposal_sent': 'file-text',
            'deal_closed_won': 'check-circle',
            'deal_closed_lost': 'x-circle',
            'task_created': 'plus-square',
            'task_completed': 'check-square',
            'task_overdue': 'alert-triangle',
            'mission_completed': 'target',
            'boss_progress': 'trending-up',
            'boss_defeated': 'award',
            'tokens_earned': 'coin',
            'xp_gained': 'zap',
            'level_up': 'trophy',
            'reward_claimed': 'gift',
            'streak_milestone': 'flame',
            'lead_created': 'user-plus',
            'lead_updated': 'edit',
            'lead_revived': 'refresh-cw',
        }
        action_type = getattr(self, 'action_type', '')
        return icons.get(action_type, 'activity')
    
    def get_color(self):
        colors = {
            'outreach_logged': 'blue',
            'lead_contacted': 'indigo',
            'call_booked': 'green',
            'proposal_sent': 'purple',
            'deal_closed_won': 'emerald',
            'deal_closed_lost': 'red',
            'task_created': 'slate',
            'task_completed': 'green',
            'task_overdue': 'orange',
            'mission_completed': 'yellow',
            'boss_progress': 'cyan',
            'boss_defeated': 'gold',
            'tokens_earned': 'amber',
            'xp_gained': 'violet',
            'level_up': 'purple',
            'reward_claimed': 'pink',
            'streak_milestone': 'orange',
            'lead_created': 'green',
            'lead_updated': 'yellow',
            'lead_revived': 'cyan',
        }
        action_type = getattr(self, 'action_type', '')
        return colors.get(action_type, 'gray')
    
    def is_highlight(self):
        action_type = getattr(self, 'action_type', '')
        return action_type in ['boss_defeated', 'level_up', 'deal_closed_won', 'xp_gained']
    
    @staticmethod
    def log_activity(action_type, description, related_id=None, related_object_type=None, xp_earned=0, tokens_earned=0):
        return ActivityLog.insert({
            'action_type': action_type,
            'description': description,
            'related_id': related_id,
            'related_object_type': related_object_type,
            'timestamp': tz.now_iso()
        })


class Note(SupabaseModel):
    __tablename__ = 'notes'
    
    def get_tags_list(self):
        if not hasattr(self, 'tags') or not self.tags:
            return []
        if isinstance(self, str): # Handle potential parsing issues
            return [t.strip() for t in self.split(',') if t.strip()]
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def get_preview(self, length=150):
        if not hasattr(self, 'content') or not self.content:
            return ""
        content = self.content
        if len(content) > length:
            return content[:length-3] + "..."
        return content

    @classmethod
    def _parse_row(cls, row: dict):
        obj = super()._parse_row(row)
        if obj:
            if hasattr(obj, 'created_at') and obj.created_at:
                obj.created_at = parse_datetime(obj.created_at)
            if hasattr(obj, 'updated_at') and obj.updated_at:
                obj.updated_at = parse_datetime(obj.updated_at)
        return obj


class WinsLog(SupabaseModel):
    __tablename__ = 'wins_log'
    
    @classmethod
    def _parse_row(cls, row: dict):
        if row is None:
            return None
        obj = cls(**row)
        # Handle missing created_at in some environments
        if hasattr(obj, 'created_at') and obj.created_at:
            obj.created_at = parse_datetime(obj.created_at)
        return obj


class MonthlyReview(SupabaseModel):
    __tablename__ = 'monthly_reviews'
    
    def get_content(self):
        content = getattr(self, 'content', None)
        if content:
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except:
                    return {}
            return content
        return {}
    
    @staticmethod
    def save_review(year_month, content):
        existing = MonthlyReview.get_first({'year_month': year_month})
        content_json = json.dumps(content) if isinstance(content, dict) else content
        
        if existing:
            return MonthlyReview.update_by_id(existing.id, {
                'content': content_json,
                'generated_at': tz.now_iso()
            })
        else:
            return MonthlyReview.insert({
                'year_month': year_month,
                'content': content_json,
                'generated_at': tz.now_iso()
            })


class FocusSession(SupabaseModel):
    __tablename__ = 'focus_sessions'


class BattlePass(SupabaseModel):
    __tablename__ = 'battle_passes'


class BattlePassTier(SupabaseModel):
    __tablename__ = 'battle_pass_tiers'


class FreelancingIncome(SupabaseModel):
    __tablename__ = 'freelance_jobs'
    
    @staticmethod
    def category_choices():
        return ['photography', 'one_off_job', 'consulting', 'side_project', 'cash_work', 'other']
