//! Client: the driver's machine controls. While a control's key is held (BM_Control: e.g.
//! PageUp / PageDown), the server moves the joint it works; on release it stops where it is.
modded class MissionGameplay
{
	protected ref array<int> m_BMDirs = {0, 0, 0, 0};
	protected BM_Machine m_BMMachine;	//!< the machine the last commands went to

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		BMUpdateControls();
	}

	protected void BMUpdateControls()
	{
		PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
		BM_Machine machine;
		if (player && player.GetCommand_Vehicle())
		{
			machine = BM_Machine.Cast(player.GetCommand_Vehicle().GetTransport());
			if (machine && machine.CrewMember(0) != player)
				machine = null;
		}

		// Left the machine (or another one) mid-move: stop what was moving
		if (m_BMMachine && m_BMMachine != machine)
		{
			for (int k = 0; k < BM_Control.COUNT; k++)
			{
				if (m_BMDirs[k] != 0)
				{
					GetGame().RPCSingleParam(m_BMMachine, BM_RPC.CONTROL, new Param2<int, int>(k, 0), true);
					m_BMMachine.OnControlLocal(k, 0);
				}
				m_BMDirs[k] = 0;
			}
		}
		m_BMMachine = machine;
		if (!machine)
			return;

		bool menu = GetUIManager().GetMenu() != null;
		for (int c = 0; c < BM_Control.COUNT; c++)
		{
			if (!machine.HasControl(c))
				continue;
			int dir = 0;
			if (!menu)
			{
				if (GetUApi().GetInputByName(BM_Control.KeyUp(c)).LocalHold())
					dir = 1;
				else if (GetUApi().GetInputByName(BM_Control.KeyDown(c)).LocalHold())
					dir = -1;
			}
			if (dir != m_BMDirs[c])
			{
				GetGame().RPCSingleParam(machine, BM_RPC.CONTROL, new Param2<int, int>(c, dir), true);
				machine.OnControlLocal(c, dir);
				m_BMDirs[c] = dir;
			}
		}
	}
}
